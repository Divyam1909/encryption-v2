"""
FHE Encryption Tests
====================
Comprehensive tests for the homomorphic encryption system.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fhe_core.encryption_core import FHEEngine, EncryptedVector
from fhe_core.key_manager import KeyManager


class TestFHEEngine:
    """Tests for FHEEngine class"""
    
    @pytest.fixture
    def engine(self):
        """Create FHE engine for testing"""
        return FHEEngine()
    
    def test_engine_creation(self, engine):
        """Test FHE engine initializes correctly"""
        assert engine is not None
        assert engine.context is not None
        assert engine.context.is_private()  # Should have secret key
        
        info = engine.get_info()
        assert info['scheme'] == 'CKKS'
        assert info['has_secret_key'] is True
    
    def test_encrypt_decrypt_roundtrip(self, engine):
        """Test encryption followed by decryption returns original values"""
        original = [1.5, 2.5, 3.5, 4.5, 5.5]
        
        encrypted = engine.encrypt(original, "test")
        assert isinstance(encrypted, EncryptedVector)
        assert encrypted.vector_size == len(original)
        
        decrypted = engine.decrypt(encrypted)
        
        # Check values match within CKKS tolerance
        for o, d in zip(original, decrypted):
            assert abs(o - d) < 1e-4, f"Expected {o}, got {d}"
    
    def test_encrypt_numpy_array(self, engine):
        """Test encryption of numpy arrays"""
        original = np.array([10.0, 20.0, 30.0])
        
        encrypted = engine.encrypt(original, "numpy_test")
        decrypted = engine.decrypt(encrypted)
        
        for o, d in zip(original, decrypted):
            assert abs(o - d) < 1e-4
    
    def test_homomorphic_addition(self, engine):
        """Test homomorphic addition: E(a) + E(b) = E(a+b)"""
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        expected = [5.0, 7.0, 9.0]
        
        enc_a = engine.encrypt(a, "a")
        enc_b = engine.encrypt(b, "b")
        
        enc_result = engine.add_encrypted(enc_a, enc_b)
        decrypted = engine.decrypt(enc_result)
        
        for e, d in zip(expected, decrypted):
            assert abs(e - d) < 1e-4, f"Expected {e}, got {d}"
    
    def test_homomorphic_addition_plain(self, engine):
        """Test adding plaintext to encrypted: E(a) + b = E(a+b)"""
        a = [10.0, 20.0, 30.0]
        b = 5.0
        expected = [15.0, 25.0, 35.0]
        
        enc_a = engine.encrypt(a, "a")
        enc_result = engine.add_plain(enc_a, b)
        decrypted = engine.decrypt(enc_result)
        
        for e, d in zip(expected, decrypted):
            assert abs(e - d) < 1e-4
    
    def test_homomorphic_multiplication(self, engine):
        """Test homomorphic multiplication: E(a) * E(b) = E(a*b)"""
        a = [2.0, 3.0, 4.0]
        b = [5.0, 6.0, 7.0]
        expected = [10.0, 18.0, 28.0]
        
        enc_a = engine.encrypt(a, "a")
        enc_b = engine.encrypt(b, "b")
        
        enc_result = engine.multiply_encrypted(enc_a, enc_b)
        decrypted = engine.decrypt(enc_result)
        
        for e, d in zip(expected, decrypted):
            assert abs(e - d) < 1e-3, f"Expected {e}, got {d}"
    
    def test_homomorphic_multiplication_plain(self, engine):
        """Test multiplying by plaintext: E(a) * b = E(a*b)"""
        a = [1.0, 2.0, 3.0]
        b = 2.5
        expected = [2.5, 5.0, 7.5]
        
        enc_a = engine.encrypt(a, "a")
        enc_result = engine.multiply_plain(enc_a, b)
        decrypted = engine.decrypt(enc_result)
        
        for e, d in zip(expected, decrypted):
            assert abs(e - d) < 1e-4
    
    def test_homomorphic_subtraction(self, engine):
        """Test homomorphic subtraction: E(a) - E(b) = E(a-b)"""
        a = [10.0, 20.0, 30.0]
        b = [3.0, 7.0, 10.0]
        expected = [7.0, 13.0, 20.0]
        
        enc_a = engine.encrypt(a, "a")
        enc_b = engine.encrypt(b, "b")
        
        enc_result = engine.subtract_encrypted(enc_a, enc_b)
        decrypted = engine.decrypt(enc_result)
        
        for e, d in zip(expected, decrypted):
            assert abs(e - d) < 1e-4
    
    def test_homomorphic_mean(self, engine):
        """Test computing mean on encrypted data"""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        expected_mean = 30.0
        
        encrypted = engine.encrypt(values, "test")
        enc_mean = engine.compute_mean(encrypted)
        decrypted = engine.decrypt(enc_mean)
        
        # Mean should be in first element
        assert abs(decrypted[0] - expected_mean) < 1e-3
    
    def test_celsius_to_fahrenheit_conversion(self, engine):
        """Test temperature conversion on encrypted data"""
        celsius = [0.0, 25.0, 100.0]
        # F = C * 1.8 + 32
        expected_fahrenheit = [32.0, 77.0, 212.0]
        
        enc_c = engine.encrypt(celsius, "celsius")
        
        # Multiply by 1.8
        enc_scaled = engine.multiply_plain(enc_c, 1.8)
        # Add 32
        enc_f = engine.add_plain(enc_scaled, 32.0)
        
        decrypted = engine.decrypt(enc_f)
        
        for e, d in zip(expected_fahrenheit, decrypted):
            assert abs(e - d) < 1e-2, f"Expected {e}°F, got {d:.2f}°F"
    
    def test_context_serialization(self, engine):
        """Test context can be serialized and restored"""
        original_data = [1.0, 2.0, 3.0]
        
        # Encrypt with original engine
        encrypted = engine.encrypt(original_data, "test")
        
        # Get serialized context (with secret key)
        secret_ctx = engine.get_secret_context()
        
        # Create new engine from context
        new_engine = FHEEngine.from_context(secret_ctx, has_secret_key=True)
        
        # Should be able to decrypt
        decrypted = new_engine.decrypt(encrypted)
        
        for o, d in zip(original_data, decrypted):
            assert abs(o - d) < 1e-4
    
    def test_public_context_cannot_decrypt(self, engine):
        """Test public context cannot decrypt data"""
        original_data = [1.0, 2.0, 3.0]
        
        # Encrypt with full engine
        encrypted = engine.encrypt(original_data, "test")
        
        # Get public context (no secret key)
        public_ctx = engine.get_public_context()
        
        # Create engine from public context
        public_engine = FHEEngine.from_context(public_ctx, has_secret_key=False)
        
        # Should NOT be able to decrypt
        with pytest.raises(ValueError, match="secret key"):
            public_engine.decrypt(encrypted)
    
    def test_checksum_verification(self, engine):
        """Test ciphertext integrity verification"""
        encrypted = engine.encrypt([1.0, 2.0], "test")
        
        # Should verify successfully
        assert engine.verify_encrypted(encrypted) is True
        
        # Corrupt the ciphertext
        corrupted = EncryptedVector(
            ciphertext=encrypted.ciphertext[:-10] + b'corrupted!',
            timestamp=encrypted.timestamp,
            sensor_type=encrypted.sensor_type,
            vector_size=encrypted.vector_size,
            checksum=encrypted.checksum  # Original checksum
        )
        
        # Should fail verification
        assert engine.verify_encrypted(corrupted) is False
    
    def test_batch_operations(self, engine):
        """Test batch encryption and decryption"""
        data_list = [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0]
        ]
        
        encrypted_list = engine.batch_encrypt(data_list, ["a", "b", "c"])
        assert len(encrypted_list) == 3
        
        decrypted_list = engine.batch_decrypt(encrypted_list)
        assert len(decrypted_list) == 3
        
        for original, decrypted in zip(data_list, decrypted_list):
            for o, d in zip(original, decrypted):
                assert abs(o - d) < 1e-4


class TestKeyManager:
    """Tests for KeyManager class"""
    
    @pytest.fixture
    def key_manager(self, tmp_path):
        """Create key manager with temp directory"""
        return KeyManager(str(tmp_path / ".keys"))
    
    @pytest.fixture
    def engine(self):
        """Create FHE engine"""
        return FHEEngine()
    
    def test_key_manager_creation(self, key_manager):
        """Test key manager initializes correctly"""
        assert key_manager is not None
        stats = key_manager.get_stats()
        assert stats['total_devices'] == 0
    
    def test_registration_code_generation(self, key_manager):
        """Test registration code generation"""
        code = key_manager.generate_registration_code("Test Device")
        
        assert code is not None
        assert len(code) == 6
        assert code.isalnum()
    
    def test_registration_code_validation(self, key_manager):
        """Test registration code validation"""
        code = key_manager.generate_registration_code("Test Device")
        
        # Valid code
        valid, message = key_manager.validate_registration_code(code)
        assert valid is True
        assert "Test Device" in message
        
        # Invalid code
        valid, message = key_manager.validate_registration_code("INVALID")
        assert valid is False
    
    def test_device_registration(self, key_manager, engine):
        """Test device registration flow"""
        # Set FHE contexts
        key_manager.set_fhe_contexts(
            engine.get_public_context(),
            engine.get_secret_context()
        )
        
        # Generate code
        code = key_manager.generate_registration_code("Mobile Device")
        
        # Register device
        fingerprint = "test_fingerprint_12345"
        device = key_manager.register_device(code, fingerprint)
        
        assert device is not None
        assert device.device_name == "Mobile Device"
        assert device.is_trusted is True
        assert device.trust_token is not None
    
    def test_trust_verification(self, key_manager, engine):
        """Test trust token verification"""
        key_manager.set_fhe_contexts(
            engine.get_public_context(),
            engine.get_secret_context()
        )
        
        code = key_manager.generate_registration_code("Trusted Device")
        device = key_manager.register_device(code, "fingerprint123")
        
        # Verify with correct token
        is_trusted = key_manager.verify_trust_token(device.device_id, device.trust_token)
        assert is_trusted is True
        
        # Verify with wrong token
        is_trusted = key_manager.verify_trust_token(device.device_id, "wrong_token")
        assert is_trusted is False
    
    def test_device_revocation(self, key_manager, engine):
        """Test device revocation"""
        key_manager.set_fhe_contexts(
            engine.get_public_context(),
            engine.get_secret_context()
        )
        
        code = key_manager.generate_registration_code("Revoke Test")
        device = key_manager.register_device(code, "fingerprint456")
        
        # Initially trusted
        assert key_manager.verify_trust_token(device.device_id, device.trust_token) is True
        
        # Revoke
        key_manager.revoke_device(device.device_id)
        
        # No longer trusted
        assert key_manager.verify_trust_token(device.device_id, device.trust_token) is False


class TestSensors:
    """Tests for sensor simulation"""
    
    def test_temperature_sensor(self):
        """Test temperature sensor readings"""
        from sensors.sensors import TemperatureSensor
        
        sensor = TemperatureSensor(ambient_temp=25.0)
        readings = sensor.get_values(count=10)
        
        assert len(readings) == 10
        for r in readings:
            assert -40 <= r <= 80  # Within sensor range
            assert 15 <= r <= 35   # Roughly around ambient
    
    def test_ultrasonic_sensor(self):
        """Test ultrasonic sensor readings"""
        from sensors.sensors import UltrasonicSensor
        
        sensor = UltrasonicSensor(target_distance=100.0)
        readings = sensor.get_values(count=10)
        
        assert len(readings) == 10
        for r in readings:
            assert 2 <= r <= 400  # Within sensor range
            assert 50 <= r <= 150  # Roughly around target (wider tolerance for noise)
    
    def test_sensor_array(self):
        """Test sensor array with multiple sensors"""
        from sensors.sensors import SensorArray, TemperatureSensor, UltrasonicSensor
        
        array = SensorArray("Test Array")
        array.add_sensor(TemperatureSensor("temp1"))
        array.add_sensor(UltrasonicSensor("dist1"))
        
        assert len(array) == 2
        
        readings = array.read_all_values()
        assert "temp1" in readings
        assert "dist1" in readings


class TestEndToEnd:
    """End-to-end integration tests"""
    
    def test_full_encryption_workflow(self):
        """Test complete encryption workflow"""
        engine = FHEEngine()
        
        # Simulate sensor readings
        temperature_readings = [25.5, 26.1, 25.8, 26.3, 25.9]
        
        # Encrypt
        encrypted = engine.encrypt(temperature_readings, "temperature")
        
        # Display for "untrusted"
        ciphertext_preview = encrypted.get_display_ciphertext(40)
        assert len(ciphertext_preview) <= 43  # 40 + "..."
        
        # Compute mean on encrypted (server-side)
        enc_mean = engine.compute_mean(encrypted)
        
        # Decrypt (client-side)
        decrypted_mean = engine.decrypt(enc_mean)
        expected_mean = sum(temperature_readings) / len(temperature_readings)
        
        assert abs(decrypted_mean[0] - expected_mean) < 1e-3
    
    def test_trusted_vs_untrusted_access(self, tmp_path):
        """Test that untrusted entities can't decrypt"""
        engine = FHEEngine()
        key_manager = KeyManager(str(tmp_path / ".keys"))
        
        # Setup
        key_manager.set_fhe_contexts(
            engine.get_public_context(),
            engine.get_secret_context()
        )
        
        # Original data
        secret_data = [42.0, 84.0, 126.0]
        encrypted = engine.encrypt(secret_data, "secret")
        
        # Untrusted entity (public context only)
        public_engine = FHEEngine.from_context(
            engine.get_public_context(),
            has_secret_key=False
        )
        
        # Untrusted cannot decrypt
        with pytest.raises(ValueError):
            public_engine.decrypt(encrypted)
        
        # Trusted entity (has secret context via registration)
        code = key_manager.generate_registration_code("Trusted")
        device = key_manager.register_device(code, "fp")
        
        trusted_engine = FHEEngine.from_context(
            device.secret_context,
            has_secret_key=True
        )
        
        # Trusted can decrypt
        decrypted = trusted_engine.decrypt(encrypted)
        for orig, dec in zip(secret_data, decrypted):
            assert abs(orig - dec) < 1e-4


# ==================== RUN TESTS ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])