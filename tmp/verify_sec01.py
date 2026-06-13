import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Flask and SQLAlchemy before importing services
sys.modules['flask'] = MagicMock()
sys.modules['flask_sqlalchemy'] = MagicMock()
sys.modules['flask_login'] = MagicMock()
sys.modules['flask_jwt_extended'] = MagicMock()
sys.modules['flask_limiter'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['flask_talisman'] = MagicMock()
sys.modules['flask_wtf'] = MagicMock()
sys.modules['flask_wtf.csrf'] = MagicMock()

# Import the actual logic
from app.utils.security import generate_signed_qr, verify_signed_qr
from app.services.asset_service import AssetService
from app.services.tracking_service import TrackingService

# Implementation of verification loop
def test_sec_01():
    print("--- Testing SEC-01: QR Signing Logic ---")
    
    # Need to mock current_app.config for generate_signed_qr
    with patch('app.utils.security.current_app') as mock_app:
        mock_app.config = {"SECRET_KEY": "test-secret-key-12345"}
        
        payload = "asset:1:ASSET-001"
        signed = generate_signed_qr(payload)
        print(f"Payload: {payload}")
        print(f"Signed:  {signed}")
        
        if signed.startswith(payload + ":") and len(signed) > len(payload) + 1:
            print("✅ SUCCESS: Signature appended.")
        else:
            print("❌ FAILURE: Signature missing or wrong format.")
            return False
            
        verify_ok = verify_signed_qr(signed)
        if verify_ok == payload:
            print("✅ SUCCESS: Verification passed for valid signature.")
        else:
            print("❌ FAILURE: Verification failed for valid signature.")
            return False
            
        tampered = signed[:-1] + ("0" if signed[-1] != "0" else "1")
        verify_fail = verify_signed_qr(tampered)
        if verify_fail is None:
            print("✅ SUCCESS: Tampered signature rejected.")
        else:
            print("❌ FAILURE: Tampered signature ACCEPTED.")
            return False

    print("\n--- Testing SEC-01: Service Integration ---")
    
    # Mock AssetRepository
    mock_repo = MagicMock()
    mock_repo.exists_asset_code.return_value = False
    mock_repo.exists_serial.return_value = False
    mock_repo.create_asset.side_effect = lambda org_id, data, session: MagicMock(asset_code=data['asset_code'], qr_code_data=data['qr_code_data'])
    
    # Mock db.session
    mock_session = MagicMock()
    
    # Mock organization/department models
    with patch('app.models.organization.Department') as mock_dept_model, \
         patch('app.services.asset_service.datetime') as mock_dt, \
         patch('app.utils.security.current_app') as mock_app:
            
        mock_app.config = {"SECRET_KEY": "test-secret-key-12345"}
        mock_dt.utcnow.return_value = MagicMock(date=lambda: MagicMock())
        mock_dt.utcnow.return_value.date.return_value = MagicMock()
        
        service = AssetService(repository=mock_repo, session=mock_session)
        
        asset_data = {
            "asset_code": "SEC-FIX-01",
            "name": "Secure Asset",
            "department_id": 1,
            "purchase_date": MagicMock(), # Mocked to avoid date comparison issues
            "purchase_value": 1000,
            "useful_life": 5,
            "depreciation_method": "straight_line"
        }
        
        # Test creation
        with patch('app.models.organization.Department.query') as mock_dept_query:
            mock_dept_query.filter_by.return_value.first.return_value = MagicMock(id=1)
            
            new_asset = service.create_asset(1, asset_data)
            print(f"Asset Service generated QR: {new_asset.qr_code_data}")
            
            if "SEC-FIX-01" in new_asset.qr_code_data and ":" in new_asset.qr_code_data:
                print("✅ SUCCESS: AssetService generated signed QR.")
            else:
                print("❌ FAILURE: AssetService failed to sign QR.")
                return False

    return True

if __name__ == "__main__":
    if test_sec_01():
        print("\nSEC-01 VERIFIED SUCCESSFULLY")
        sys.exit(0)
    else:
        print("\nSEC-01 VERIFICATION FAILED")
        sys.exit(1)
