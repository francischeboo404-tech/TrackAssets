from app import db
from app.models import transfer, inventory


class TransferRepository:
    """Repository encapsulating ORM queries for transfers."""

    def create_request(
        self,
        org_id,
        asset_id,
        requested_by,
        from_dept_id,
        to_dept_id,
        requested_location=None,
        comment=None,
        session=None,
    ):
        sess = session or db.session
        req = transfer.TransferRequest(
            organisation_id=org_id,
            asset_id=asset_id,
            requested_by=requested_by,
            from_department_id=from_dept_id,
            to_department_id=to_dept_id,
            requested_location=requested_location,
            comment=comment,
        )
        sess.add(req)
        return req

    def get_request(self, request_id, org_id, status=None):
        q = transfer.TransferRequest.query.filter_by(
            id=request_id, organisation_id=org_id
        )
        if status:
            q = q.filter_by(status=status)
        return q.first()

    def find_requests(
        self, org_id, status=None, page=1, per_page=50, user_filter=None
    ):
        from sqlalchemy.orm import joinedload

        q = transfer.TransferRequest.query.options(
            joinedload(transfer.TransferRequest.requester),
            joinedload(transfer.TransferRequest.from_department),
            joinedload(transfer.TransferRequest.to_department),
        ).filter_by(organisation_id=org_id)
        if status:
            q = q.filter_by(status=status)
        if user_filter is not None:
            q = q.filter(user_filter)
        return q.order_by(
            transfer.TransferRequest.requested_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

    def get_transfer_history_logs(self, org_id, asset_id):
        # Use audit logs stored in inventory.AuditLog for transfer entries
        return (
            inventory.AuditLog.query.filter(
                inventory.AuditLog.organisation_id == org_id,
                inventory.AuditLog.entity_type == "asset",
                inventory.AuditLog.entity_id == asset_id,
                inventory.AuditLog.action == "ASSET_TRANSFER",
            )
            .order_by(inventory.AuditLog.created_at.desc())
            .all()
        )
