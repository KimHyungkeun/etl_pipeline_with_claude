"""Unit tests for configuration settings."""
import pytest
from pathlib import Path
from app.core.config import Settings, BASE_DIR


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.app_name == "Spark Cluster API"
        assert settings.debug is False
        assert settings.spark_master_url == "http://localhost:8080"
        assert settings.spark_submit_master == "spark://localhost:7077"
        assert settings.spark_home == "/home/hkkim/spark"

    def test_custom_settings(self):
        """Test settings with custom values."""
        settings = Settings(
            app_name="Custom Spark API",
            debug=True,
            spark_master_url="http://192.168.1.100:8080",
            spark_submit_master="spark://192.168.1.100:7077",
            spark_home="/custom/spark",
        )

        assert settings.app_name == "Custom Spark API"
        assert settings.debug is True
        assert settings.spark_master_url == "http://192.168.1.100:8080"
        assert settings.spark_submit_master == "spark://192.168.1.100:7077"
        assert settings.spark_home == "/custom/spark"

    def test_base_dir_is_correct(self):
        """Test BASE_DIR points to project root."""
        # BASE_DIR should point to spark-fastapi directory
        assert BASE_DIR.name == "spark-fastapi"
        assert (BASE_DIR / "app").exists()
        assert (BASE_DIR / "pyproject.toml").exists()

    def test_spark_master_url_format(self):
        """Test Spark Master URL format validation."""
        settings = Settings(spark_master_url="http://localhost:8080")

        assert settings.spark_master_url.startswith("http")
        assert "8080" in settings.spark_master_url

    def test_spark_submit_master_format(self):
        """Test Spark submit master URL format."""
        settings = Settings(spark_submit_master="spark://localhost:7077")

        assert settings.spark_submit_master.startswith("spark://")
        assert "7077" in settings.spark_submit_master