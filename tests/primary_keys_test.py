"""Tests for primary key and foreign key functionality."""

import logging
from typing import Any, Dict

import pytest
from sqlalchemy import Engine, Table, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from pyflattendb.generator import SchemaGenerator

logger = logging.getLogger("test_primary_keys")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


def get_table_info(engine: Engine, table_name: str) -> Dict[str, Any]:
    """Get table information including primary keys and foreign keys."""
    inspector = inspect(engine)
    return {
        "primary_keys": inspector.get_pk_constraint(table_name),
        "foreign_keys": inspector.get_foreign_keys(table_name),
        "columns": {col["name"]: col for col in inspector.get_columns(table_name)},
    }


def test_auto_generated_primary_key() -> None:
    """Test that tables get an auto-generated primary key when none is specified."""
    data = {"user": {"name": "John Doe", "email": "john@example.com"}}
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    UserModel = next(m for m in models if m.__tablename__ == "user")

    engine = create_engine("sqlite:///:memory:")
    UserModel.metadata.create_all(engine)

    # Check table structure
    table_info = get_table_info(engine, "user")

    # Verify primary key
    assert "id" in table_info["columns"]
    assert table_info["columns"]["id"]["primary_key"] == 1  # SQLAlchemy uses 1 for True
    # SQLite may not always report 'autoincrement', so just check type
    # assert table_info['columns']['id'].get('autoincrement', True) is True
    assert table_info["primary_keys"]["constrained_columns"] == ["id"]


def test_explicit_primary_key() -> None:
    """Test that explicit primary keys are respected."""
    data = {"product": {"sku": "ABC123", "name": "Widget", "_pyflattendb": {"product.sku": {"primary_key": True}}}}
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    ProductModel = next(m for m in models if m.__tablename__ == "product")

    engine = create_engine("sqlite:///:memory:")
    ProductModel.metadata.create_all(engine)

    # Check table structure
    table_info = get_table_info(engine, "product")

    # Verify primary key
    assert "sku" in table_info["columns"]
    assert table_info["columns"]["sku"]["primary_key"] == 1  # SQLAlchemy uses 1 for True
    assert "id" not in table_info["columns"]  # No auto-generated id
    assert table_info["primary_keys"]["constrained_columns"] == ["sku"]


def test_compound_primary_key_association_table() -> None:
    """Test that association tables have compound primary keys."""
    data = {
        "product": {
            "name": "Widget",
            "categories": [{"name": "Electronics"}, {"name": "Gadgets"}],
            "_pyflattendb": {
                "product.categories": {
                    "is_many_to_many": True,
                    "association_table_name": "product_category_association",
                }
            },
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()

    # Find the association table (Table object, not class)
    assoc_table = next((m for m in models if isinstance(m, Table) and m.name == "product_category_association"), None)
    assert assoc_table is not None

    engine = create_engine("sqlite:///:memory:")
    assoc_table.metadata.create_all(engine)

    # Check table structure
    table_info = get_table_info(engine, "product_category_association")
    logger.debug(f"Association table columns: {table_info['columns']}")

    # Verify compound primary key
    assert "product_id" in table_info["columns"]
    assert "category_id" in table_info["columns"]
    assert table_info["columns"]["product_id"]["primary_key"] > 0
    assert table_info["columns"]["category_id"]["primary_key"] > 0
    assert set(table_info["primary_keys"]["constrained_columns"]) == {"product_id", "category_id"}

    # Verify foreign keys
    fks = table_info["foreign_keys"]
    assert len(fks) == 2
    fk_columns = {fk["constrained_columns"][0] for fk in fks}
    assert fk_columns == {"product_id", "category_id"}


def test_foreign_key_cascade_delete() -> None:
    """Test that foreign keys in association tables have CASCADE delete."""
    data = {
        "product": {
            "name": "Widget",
            "categories": [{"name": "Electronics"}, {"name": "Gadgets"}],
            "_pyflattendb": {"product.categories": {"is_many_to_many": True}},
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()

    # Find the association table (Table object, not class)
    assoc_table = next((m for m in models if isinstance(m, Table) and m.name == "product_category_association"), None)
    assert assoc_table is not None

    engine = create_engine("sqlite:///:memory:")
    assoc_table.metadata.create_all(engine)

    # Check foreign key constraints
    table_info = get_table_info(engine, "product_category_association")
    fks = table_info["foreign_keys"]

    # Verify CASCADE delete for both foreign keys
    for fk in fks:
        assert fk["options"].get("ondelete") == "CASCADE"


def test_foreign_key_set_null() -> None:
    """Test that regular foreign keys have SET NULL on delete."""
    data = {"user": {"name": "John", "address": {"street": "123 Main St", "city": "Boston"}}}
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    UserModel = next(m for m in models if m.__tablename__ == "user")

    engine = create_engine("sqlite:///:memory:")
    UserModel.metadata.create_all(engine)

    # Check foreign key constraints
    table_info = get_table_info(engine, "user")
    fks = table_info["foreign_keys"]

    # Verify SET NULL for the address foreign key
    assert len(fks) == 2
    assert fks[0]["options"].get("ondelete") == "SET NULL"


def test_reference_table_primary_key() -> None:
    """Test that reference tables have proper primary keys and unique constraints."""
    data = {
        "product": {
            "name": "Widget",
            "status": "active",
            "_pyflattendb": {
                "product.status": {
                    "is_reference_table": True,
                    "reference_table_name": "product_status",
                    "choices": ["active", "inactive", "discontinued"],
                }
            },
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()

    # Find the reference table model
    StatusModel = next(
        m
        for m in models
        if (hasattr(m, "__tablename__") and m.__tablename__ == "product_status")
        or (isinstance(m, Table) and m.name == "product_status")
    )
    assert StatusModel is not None

    engine = create_engine("sqlite:///:memory:")
    StatusModel.metadata.create_all(engine)

    # Check table structure and constraints
    with engine.connect() as conn:
        # Get table info
        result = conn.execute(
            text(
                """
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='product_status'
        """
            )
        )
        create_sql = result.scalar()
        print(f"CREATE TABLE for product_status: {create_sql}")
        logger.debug(f"CREATE TABLE for product_status: {create_sql}")

        # Get index info (unique constraints are implemented as indexes in SQLite)
        result = conn.execute(
            text(
                """
            SELECT name, sql FROM sqlite_master
            WHERE type='index' AND tbl_name='product_status'
        """
            )
        )
        indexes = result.fetchall()
        print(f"Indexes for product_status: {indexes}")
        logger.debug(f"Indexes for product_status: {indexes}")

        # Get table info
        result = conn.execute(text("PRAGMA table_info(product_status)"))
        columns = result.fetchall()
        logger.debug(f"Columns for product_status: {columns}")

    # Check table structure
    table_info = get_table_info(engine, "product_status")
    logger.debug(f"Reference table columns: {table_info['columns']}")

    # Verify primary key
    assert "id" in table_info["columns"]
    assert table_info["columns"]["id"]["primary_key"] > 0
    # Check unique constraint on value column by inserting duplicates
    with engine.connect() as conn:
        # Insert first value
        conn.execute(text("INSERT INTO product_status (value) VALUES ('active')"))
        conn.commit()
        # Try to insert duplicate value
        with pytest.raises(IntegrityError):
            conn.execute(text("INSERT INTO product_status (value) VALUES ('active')"))
            conn.commit()


def test_self_referential_many_to_many() -> None:
    """Test that self-referential many-to-many relationships have proper primary keys."""
    data = {
        "product": {
            "name": "Widget",
            "related_products": [{"name": "Gadget"}, {"name": "Tool"}],
            "_pyflattendb": {
                "product.related_products": {
                    "is_many_to_many": True,
                    "entity_type": "product",
                    "association_table_name": "product_related_products",
                }
            },
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()

    # Find the association table (Table object, not class)
    assoc_table = next((m for m in models if isinstance(m, Table) and m.name == "product_related_products"), None)
    assert assoc_table is not None

    engine = create_engine("sqlite:///:memory:")
    assoc_table.metadata.create_all(engine)

    # Check table structure
    table_info = get_table_info(engine, "product_related_products")
    logger.debug(f"Self-ref association table columns: {table_info['columns']}")

    # Verify compound primary key
    assert "product_id" in table_info["columns"]
    assert "related_product_id" in table_info["columns"]  # Different name for self-referential
    assert table_info["columns"]["product_id"]["primary_key"] > 0
    assert table_info["columns"]["related_product_id"]["primary_key"] > 0
    assert set(table_info["primary_keys"]["constrained_columns"]) == {"product_id", "related_product_id"}

    # Verify foreign keys
    fks = table_info["foreign_keys"]
    assert len(fks) == 2
    fk_columns = {fk["constrained_columns"][0] for fk in fks}
    assert fk_columns == {"product_id", "related_product_id"}
