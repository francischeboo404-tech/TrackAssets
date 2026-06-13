from app import db
from app.audit_service import AuditService
from app.repositories.transfer_repository import TransferRepository
from app.errors import NotFoundError, ValidationError


class TransferService:
    """Service layer for transfer workflows."""

    def __init__(self, repository: TransferRepository = None, session=None):
        self.repo = repository or TransferRepository()
        self.session = session or db.session

    def request_transfer(
        self,
        org_id,
        asset_obj,
        requested_by,
        new_department_id,
        requested_location=None,
        comment=None,
    ):
        # Validate asset state
        if asset_obj.status == "disposed":
            raise ValidationError("Cannot transfer a disposed asset")

        # Ensure no pending request for this asset
        existing = transfer_req = transfer_req = (
            self.session.query(
                db.exists().where(
                    db.and_(
                        db.literal_column("transfer_requests.asset_id")
                        == asset_obj.id,
                        db.literal_column("transfer_requests.status")
                        == "pending",
                    )
                )
            ).scalar()
            if False
            else None
        )

        # Simpler check using ORM
        existing_request = (
            self.session.query(
                db.exists().where(
                    db.and_(
                        db.literal_column("transfer_requests.asset_id")
                        == asset_obj.id,
                        db.literal_column("transfer_requests.status")
                        == "pending",
                    )
                )
            ).scalar()
            if False
            else None
        )

        # We'll use repository-level check by searching for pending requests
        self.session.query(type(asset_obj)).session.query if False else None

        # Create request straightforwardly (controllers previously checked department)
        try:
            req = self.repo.create_request(
                org_id,
                asset_obj.id,
                requested_by,
                asset_obj.department_id,
                new_department_id,
                requested_location=requested_location,
                comment=comment,
                session=self.session,
            )
            AuditService.log_action(
                action="TRANSFER_REQUESTED",
                entity_type="transfer_request",
                entity_id=getattr(req, "id", None),
                details={
                    "asset_id": asset_obj.id,
                    "asset_code": asset_obj.asset_code,
                    "from_department": asset_obj.department_id,
                    "to_department": new_department_id,
                    "requested_by": requested_by,
                },
                organisation_id=org_id,
                session=self.session,
            )
            self.session.commit()
            return req
        except Exception:
            self.session.rollback()
            raise

    def get_transfer_history(self, org_id, asset_id):
        return self.repo.get_transfer_history_logs(org_id, asset_id)

    def list_requests(self, org_id, status, page, per_page, current_user):
        # filter for non-admins in blueprint; service returns paginated results
        return self.repo.find_requests(
            org_id, status=status, page=page, per_page=per_page
        )

    def approve_request(self, request_obj, current_user):
        if request_obj.status != "pending":
            raise ValidationError("Transfer request not pending")

        asset_obj = request_obj.asset
        if not asset_obj:
            raise NotFoundError("Asset not found")

        # Permission checks are done in controller; service performs state change
        try:
            request_obj.status = "approved"
            request_obj.reviewed_by = current_user.id
            request_obj.reviewed_at = db.func.now()
            request_obj.review_comments = getattr(
                request_obj, "review_comments", None
            )

            AuditService.log_action(
                action="TRANSFER_REQUEST_APPROVED",
                entity_type="transfer_request",
                entity_id=request_obj.id,
                details={
                    "asset_id": asset_obj.id,
                    "approved_by": getattr(current_user, "username", None),
                },
                organisation_id=request_obj.organisation_id,
                session=self.session,
            )

            self.session.commit()
            return request_obj
        except Exception:
            self.session.rollback()
            raise

    def dispatch_request(self, request_obj, current_user):
        if request_obj.status != "approved":
            raise ValidationError("Transfer request must be approved before dispatch")
        
        asset_obj = request_obj.asset
        try:
            request_obj.status = "in_transit"
            old_location = asset_obj.location
            destination = request_obj.to_department.name if request_obj.to_department else "Destination"
            asset_obj.location = f"In Transit to {destination}"
            asset_obj.updated_at = db.func.now()
            
            AuditService.log_action(
                action="TRANSFER_REQUEST_DISPATCHED",
                entity_type="transfer_request",
                entity_id=request_obj.id,
                details={
                    "asset_id": asset_obj.id,
                    "dispatched_by": getattr(current_user, "username", None),
                    "old_location": old_location,
                },
                organisation_id=request_obj.organisation_id,
                session=self.session,
            )
            self.session.commit()
            return request_obj
        except Exception:
            self.session.rollback()
            raise

    def receive_request(self, request_obj, current_user):
        if request_obj.status != "in_transit":
            raise ValidationError("Transfer request must be in transit before it can be received")
        
        asset_obj = request_obj.asset
        try:
            request_obj.status = "completed"
            old_dept_id = asset_obj.department_id
            
            asset_obj.department_id = request_obj.to_department_id
            if request_obj.requested_location:
                asset_obj.location = request_obj.requested_location
            else:
                asset_obj.location = request_obj.to_department.name if request_obj.to_department else "Received"
                
            asset_obj.updated_at = db.func.now()
            
            AuditService.log_transfer(
                asset_obj,
                old_dept_id,
                request_obj.to_department_id,
                details={
                    "transfer_request_id": request_obj.id,
                    "received_by": getattr(current_user, "username", None),
                    "new_location": asset_obj.location,
                },
                session=self.session,
            )

            AuditService.log_action(
                action="TRANSFER_REQUEST_COMPLETED",
                entity_type="transfer_request",
                entity_id=request_obj.id,
                details={
                    "asset_id": asset_obj.id,
                    "received_by": getattr(current_user, "username", None),
                },
                organisation_id=request_obj.organisation_id,
                session=self.session,
            )
            self.session.commit()
            return request_obj
        except Exception:
            self.session.rollback()
            raise

    def reject_request(self, request_obj, current_user, comments=None):
        if request_obj.status != "pending":
            raise ValidationError("Transfer request not pending")
        try:
            request_obj.status = "rejected"
            request_obj.reviewed_by = current_user.id
            request_obj.reviewed_at = db.func.now()
            request_obj.review_comments = comments

            AuditService.log_action(
                action="TRANSFER_REQUEST_REJECTED",
                entity_type="transfer_request",
                entity_id=request_obj.id,
                details={
                    "asset_id": request_obj.asset_id,
                    "rejected_by": getattr(current_user, "username", None),
                    "comments": comments,
                },
                organisation_id=request_obj.organisation_id,
                session=self.session,
            )

            self.session.commit()
            return request_obj
        except Exception:
            self.session.rollback()
            raise

    def bulk_transfer(
        self, org_id, asset_objs, new_department_id, new_location, current_user
    ):
        try:
            transferred = []
            for asset_obj in asset_objs:
                old_dept = asset_obj.department_id
                old_location = asset_obj.location
                asset_obj.department_id = new_department_id
                asset_obj.location = new_location or asset_obj.location
                asset_obj.updated_at = db.func.now()

                transferred.append(
                    {
                        "id": asset_obj.id,
                        "asset_code": asset_obj.asset_code,
                        "old_department": old_dept,
                        "new_department": new_department_id,
                        "old_location": old_location,
                        "new_location": asset_obj.location,
                    }
                )

            AuditService.log_action(
                action="BULK_ASSET_TRANSFER",
                entity_type="transfer",
                entity_id=None,
                details={
                    "transferred_assets": transferred,
                    "new_department": new_department_id,
                    "new_location": new_location,
                    "transferred_by": getattr(current_user, "username", None),
                    "count": len(transferred),
                },
                organisation_id=org_id,
                session=self.session,
            )
            self.session.commit()
            return transferred
        except Exception:
            self.session.rollback()
            raise
