import os
import unittest
import shutil
import json
from mcp_server import is_sensitive, list_project_files, get_csv_schema, write_okf_manifest

class TestOKFUpdaterMCP(unittest.TestCase):
    def setUp(self):
        self.project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "mock_data"))
        os.makedirs(self.project_dir, exist_ok=True)
        
        # Create normal files
        self.csv_path = os.path.join(self.project_dir, "sales.csv")
        with open(self.csv_path, "w") as f:
            f.write("id,value\n1,100\n2,200\n")
            
        # Create sensitive files
        self.env_path = os.path.join(self.project_dir, ".env")
        with open(self.env_path, "w") as f:
            f.write("DB_PASSWORD=abc\n")
            
        self.secret_path = os.path.join(self.project_dir, "keys_secret.json")
        with open(self.secret_path, "w") as f:
            f.write('{"api_key": "123"}\n')

    def tearDown(self):
        # Clean up files created during test
        for filename in ["sales.csv", ".env", "keys_secret.json", "okf_manifest.json", "okf_manifest.json.bak"]:
            filepath = os.path.join(self.project_dir, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass

    def test_is_sensitive(self):
        self.assertTrue(is_sensitive(".env"))
        self.assertTrue(is_sensitive(".env.local"))
        self.assertTrue(is_sensitive("config/secrets.json"))
        self.assertTrue(is_sensitive("my_api_key.txt"))
        self.assertTrue(is_sensitive("db_password.ini"))
        self.assertFalse(is_sensitive("sales.csv"))
        self.assertFalse(is_sensitive("app.py"))

    def test_list_project_files_excludes_sensitive(self):
        files = list_project_files(self.project_dir)
        self.assertIn("sales.csv", files)
        self.assertNotIn(".env", files)
        self.assertNotIn("keys_secret.json", files)

    def test_get_csv_schema_enforces_security(self):
        # Normal csv works
        schema = get_csv_schema("sales.csv", self.project_dir)
        self.assertEqual(schema["headers"], ["id", "value"])
        
        # Sensitive csv fails
        with self.assertRaises(PermissionError):
            get_csv_schema(".env", self.project_dir)
            
        with self.assertRaises(PermissionError):
            get_csv_schema("keys_secret.json", self.project_dir)

    def test_write_manifest_creates_backup(self):
        manifest_data = {"name": "test"}
        
        # First write
        res1 = write_okf_manifest(self.project_dir, manifest_data)
        self.assertIn("Successfully wrote manifest", res1)
        self.assertTrue(os.path.exists(os.path.join(self.project_dir, "okf_manifest.json")))
        
        # Second write (triggers backup)
        res2 = write_okf_manifest(self.project_dir, manifest_data)
        self.assertIn("okf_manifest.json.bak", res2)
        self.assertTrue(os.path.exists(os.path.join(self.project_dir, "okf_manifest.json.bak")))

if __name__ == "__main__":
    unittest.main()
