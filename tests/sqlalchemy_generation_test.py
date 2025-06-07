"""Tests for SQLAlchemy model generation functionality."""

from typing import Generator, Set

import pytest
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import clear_mappers

from pyflattendb.generator import SchemaGenerator


@pytest.fixture(autouse=True)
def cleanup_sqlalchemy() -> Generator[None, None, None]:
    """Clear mappers after each test to avoid SQLAlchemy warnings."""
    yield
    clear_mappers()


def get_table_names(engine: Engine) -> Set[str]:
    """Get table names from the engine."""
    insp = inspect(engine)
    return set(insp.get_table_names())


def test_basic_sqlalchemy_model_generation() -> None:
    """Test basic SQLAlchemy model generation."""
    data = {
        "user": {
            "name": "John Doe",
            "age": 30,
            "is_active": True,
            "score": 95.5,
            "_pyflattendb": {
                "user.name": {"max_len": 100},
                "user.age": {"min_value": 0, "max_value": 150},
                "user.score": {"precision": 2},
            },
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    UserModel = next(m for m in models if m.__tablename__ == "user")
    engine = create_engine("sqlite:///:memory:")
    UserModel.metadata.create_all(engine)
    table_names = get_table_names(engine)
    assert "user" in table_names
    columns = {c.name for c in UserModel.__table__.columns}
    assert {"id", "name", "age", "is_active", "score"}.issubset(columns)


def test_relationship_sqlalchemy_model_generation() -> None:
    """Test SQLAlchemy model generation with relationships."""
    data = {
        "user": {
            "name": "John Doe",
            "address": {"street": "123 Main St", "city": "Boston"},
            "orders": [{"order_id": "123", "total": 99.99}],
            "_pyflattendb": {
                "user.address": {"entity_type": "address"},
                "user.orders": {"entity_type": "order", "is_many_to_many": True},
            },
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    UserModel = next(m for m in models if m.__tablename__ == "user")
    _ = next(m for m in models if m.__tablename__ == "address")
    _ = next(m for m in models if m.__tablename__ == "order")
    engine = create_engine("sqlite:///:memory:")
    UserModel.metadata.create_all(engine)
    table_names = get_table_names(engine)
    assert {"user", "address", "order", "user_order_association"}.issubset(table_names)
    # Check foreign key columns
    assert "address_id" in UserModel.__table__.columns


def test_reference_table_sqlalchemy_generation() -> None:
    """Test SQLAlchemy model generation with reference tables."""
    data = {
        "user": {
            "name": "John Doe",
            "status": "active",
            "_pyflattendb": {
                "user.status": {
                    "is_reference_table": True,
                    "choices": ["active", "inactive", "pending"],
                    "reference_table_name": "user_status",
                }
            },
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    UserModel = next(m for m in models if hasattr(m, "__tablename__") and m.__tablename__ == "user")
    StatusModel = next(
        m
        for m in models
        if (hasattr(m, "__tablename__") and m.__tablename__ == "user_status")
        or (hasattr(m, "name") and m.name == "user_status")
    )
    engine = create_engine("sqlite:///:memory:")
    UserModel.metadata.create_all(engine)
    table_names = get_table_names(engine)
    assert {"user", "user_status"}.issubset(table_names)
    # Check reference table columns
    if hasattr(StatusModel, "columns"):
        assert "value" in StatusModel.columns
    else:
        assert "value" in StatusModel.__table__.columns


def test_nullable_and_required_fields_sqlalchemy() -> None:
    """Test SQLAlchemy model generation with nullable and required fields."""
    data = {
        "user": {
            "name": "John Doe",
            "email": None,
            "phone": "123-456-7890",
            "_pyflattendb": {"user.email": {"nullable": True}, "user.phone": {"nullable": False}},
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    UserModel = next(m for m in models if m.__tablename__ == "user")
    engine = create_engine("sqlite:///:memory:")
    UserModel.metadata.create_all(engine)
    columns = UserModel.__table__.columns
    email_col = columns["email"]
    phone_col = columns["phone"]
    assert email_col.nullable is True
    assert phone_col.nullable is False


def test_many_to_many_sqlalchemy() -> None:
    """Test SQLAlchemy model generation with many-to-many relationships."""
    data = {
        "product": {
            "name": "Widget",
            "tags": [{"name": "electronics"}, {"name": "gadget"}],
            "_pyflattendb": {"product.tags": {"is_many_to_many": True, "association_table_name": "product_tags"}},
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    ProductModel = next(m for m in models if m.__tablename__ == "product")
    _ = next(m for m in models if m.__tablename__ == "tag")
    engine = create_engine("sqlite:///:memory:")
    ProductModel.metadata.create_all(engine)
    table_names = get_table_names(engine)
    assert {"product", "tag", "product_tags"}.issubset(table_names)
    # Check association table columns
    assoc_table = ProductModel.__table__.metadata.tables["product_tags"]
    assert "product_id" in assoc_table.columns
    assert "tag_id" in assoc_table.columns


def test_circular_relationship_sqlalchemy() -> None:
    """Test SQLAlchemy model generation with circular relationships."""
    data = {
        "parent": {
            "name": "Parent",
            "children": [{"name": "Child", "parent": None}],
            "_pyflattendb": {"parent.children": {"entity_type": "child"}, "child.parent": {"entity_type": "parent"}},
        }
    }
    generator = SchemaGenerator(data)
    models = generator.generate_sqlalchemy_models()
    ParentModel = next(m for m in models if m.__tablename__ == "parent")
    ChildModel = next(m for m in models if m.__tablename__ == "child")
    engine = create_engine("sqlite:///:memory:")
    ParentModel.metadata.create_all(engine)
    table_names = get_table_names(engine)
    assert {"parent", "child"}.issubset(table_names)
    # Check foreign key columns
    assert "parent_id" in ChildModel.__table__.columns
