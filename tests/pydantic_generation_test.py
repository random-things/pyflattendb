"""Tests for Pydantic model generation functionality."""

from typing import List, Optional

import pytest
from pydantic import ValidationError

from pyflattendb.generator import SchemaGenerator


def test_basic_model_generation() -> None:
    """Test generation of a basic model with simple fields."""
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
    models = generator.generate_pydantic_models()

    assert len(models) == 1
    UserModel = models[0]

    # Test valid data
    user = UserModel(name="Jane Doe", age=25, is_active=True, score=88.5)
    assert user.name == "Jane Doe"
    assert user.age == 25
    assert user.is_active is True
    assert user.score == 88.5

    # Test validation
    with pytest.raises(ValidationError):
        UserModel(name="x" * 101)  # Name too long
    with pytest.raises(ValidationError):
        UserModel(age=-1)  # Age below minimum
    with pytest.raises(ValidationError):
        UserModel(age=151)  # Age above maximum


def test_relationship_model_generation() -> None:
    """Test generation of models with relationships."""
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
    models = generator.generate_pydantic_models()

    # Should generate 3 models: User, Address, Order
    assert len(models) == 3

    # Find our models
    UserModel = next(m for m in models if m.__name__ == "user")
    AddressModel = next(m for m in models if m.__name__ == "address")
    OrderModel = next(m for m in models if m.__name__ == "order")

    # Test relationship types
    assert UserModel.__annotations__["address"] == Optional[AddressModel]
    assert UserModel.__annotations__["orders"] == List[Optional[OrderModel]]

    # Test valid data
    address = AddressModel(street="123 Main St", city="Boston")
    order = OrderModel(order_id="123", total=99.99)
    user = UserModel(name="John Doe", address=address, orders=[order])

    assert user.name == "John Doe"
    assert user.address.street == "123 Main St"
    assert user.address.city == "Boston"
    assert len(user.orders) == 1
    assert user.orders[0].order_id == "123"
    assert user.orders[0].total == 99.99


def test_reference_table_generation() -> None:
    """Test generation of models with reference tables."""
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
    models = generator.generate_pydantic_models()

    # Should generate at least the User model
    assert any(m.__name__ == "user" or m.__name__ == "User" for m in models)


def test_nullable_fields() -> None:
    """Test handling of nullable fields."""
    data = {
        "user": {
            "name": "John Doe",
            "email": None,
            "phone": "123-456-7890",
            "_pyflattendb": {"user.email": {"nullable": True}, "user.phone": {"nullable": False}},
        }
    }

    generator = SchemaGenerator(data)
    models = generator.generate_pydantic_models()

    UserModel = models[0]

    # Test nullable field
    user = UserModel(name="John Doe", email=None, phone="123-456-7890")
    assert user.email is None

    # Test non-nullable field
    with pytest.raises(ValidationError):
        UserModel(name="John Doe", phone=None)


def test_circular_references() -> None:
    """Test handling of circular references between models."""
    data = {
        "parent": {
            "name": "Parent",
            "children": [{"name": "Child", "parent": None}],  # Will be set after creation
            "_pyflattendb": {"parent.children": {"entity_type": "child"}, "child.parent": {"entity_type": "parent"}},
        }
    }

    generator = SchemaGenerator(data)
    models = generator.generate_pydantic_models()

    # Should generate 2 models: Parent and Child
    assert len(models) == 2

    ParentModel = next(m for m in models if m.__name__ == "parent")
    ChildModel = next(m for m in models if m.__name__ == "child")

    # Test circular reference
    parent = ParentModel(name="Parent", children=[])
    child = ChildModel(name="Child", parent=parent)
    parent.children = [child]

    assert parent.name == "Parent"
    assert len(parent.children) == 1
    assert parent.children[0].name == "Child"
    assert parent.children[0].parent is parent


def test_metadata_validation() -> None:
    """Test various metadata-based validations."""
    data = {
        "product": {
            "name": "Test Product",
            "code": "ABC123",
            "price": 99.99,
            "category": "electronics",
            "_pyflattendb": {
                "product.name": {"min_len": 3, "max_len": 50},
                "product.code": {"regex": r"^[A-Z]{3}\d{3}$"},
                "product.price": {"min_value": 0, "max_value": 1000},
                "product.category": {"choices": ["electronics", "clothing", "books"]},
            },
        }
    }

    generator = SchemaGenerator(data)
    models = generator.generate_pydantic_models()

    ProductModel = models[0]

    # Test valid data
    product = ProductModel(name="Valid Product", code="XYZ789", price=99.99, category="electronics")
    assert product.name == "Valid Product"
    assert product.code == "XYZ789"
    assert product.price == 99.99
    assert product.category == "electronics"

    # Test various validations
    with pytest.raises(ValidationError):
        ProductModel(name="AB", code="XYZ789", price=99.99, category="electronics")  # Name too short

    with pytest.raises(ValidationError):
        ProductModel(name="Valid Product", code="invalid", price=99.99, category="electronics")  # Invalid code format

    with pytest.raises(ValidationError):
        ProductModel(name="Valid Product", code="XYZ789", price=-1, category="electronics")  # Price below minimum

    with pytest.raises(ValidationError):
        ProductModel(name="Valid Product", code="XYZ789", price=99.99, category="invalid")  # Invalid category
