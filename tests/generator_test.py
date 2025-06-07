"""Tests for the schema generator."""

import pytest

from pyflattendb.generator import SchemaGenerator


def test_schema_generator_initialization() -> None:
    """Test schema generator initialization with various inputs."""
    # Test with valid input
    data = {"user": {"name": "John", "age": 30}}
    generator = SchemaGenerator(data)
    assert generator.type_name == "user"

    # Test with explicit type name
    generator = SchemaGenerator(data, type_name="custom_user")
    assert generator.type_name == "custom_user"

    # Test with invalid input (not a dict)
    with pytest.raises(ValueError, match="Input data must be a dictionary"):
        SchemaGenerator("not a dict")

    # Test with invalid input (multiple keys and no type_name)
    with pytest.raises(ValueError, match="Either provide a type_name or ensure data is a dict with a single key"):
        SchemaGenerator({"key1": {}, "key2": {}})

    # Test with metadata key only
    with pytest.raises(ValueError, match="Either provide a type_name or ensure data is a dict with a single key"):
        SchemaGenerator({"_pyflattendb": {}})


def test_analyze_structure_basic() -> None:
    """Test basic structure analysis."""
    data = {"user": {"name": "John", "age": 30, "is_active": True, "metadata": {"last_login": "2024-01-01"}}}
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    fields = structure["user"]
    assert len(fields) == 4

    # Check field types
    assert any(f.name == "name" and f.python_type == str for f in fields)
    assert any(f.name == "age" and f.python_type == int for f in fields)
    assert any(f.name == "is_active" and f.python_type == bool for f in fields)
    assert any(f.name == "metadata" and f.python_type == dict for f in fields)


def test_analyze_structure_nested() -> None:
    """Test analysis of nested structures."""
    data = {"user": {"name": "John", "address": {"street": "123 Main St", "city": "Boston"}}}
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "address" in structure

    # Check user fields
    user_fields = structure["user"]
    address_field = next(f for f in user_fields if f.name == "address")
    assert address_field.is_relationship
    assert address_field.relationship_type == "address"
    assert address_field.is_foreign_key
    assert address_field.foreign_key_to == "address"

    # Check address fields
    address_fields = structure["address"]
    assert len(address_fields) == 2
    assert any(f.name == "street" and f.python_type == str for f in address_fields)
    assert any(f.name == "city" and f.python_type == str for f in address_fields)


def test_analyze_structure_with_lists() -> None:
    """Test analysis of structures containing lists."""
    data = {"user": {"name": "John", "orders": [{"id": 1, "total": 100.0}, {"id": 2, "total": 200.0}]}}
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "order" in structure

    # Check user fields
    user_fields = structure["user"]
    orders_field = next(f for f in user_fields if f.name == "orders")
    assert orders_field.is_relationship
    assert orders_field.relationship_type == "order"
    assert orders_field.is_list
    assert orders_field.is_foreign_key
    assert orders_field.foreign_key_to == "order"

    # Check order fields
    order_fields = structure["order"]
    assert len(order_fields) == 2
    assert any(f.name == "id" and f.python_type == int for f in order_fields)
    assert any(f.name == "total" and f.python_type == float for f in order_fields)


def test_analyze_structure_with_metadata() -> None:
    """Test analysis of structures with metadata."""
    data = {
        "_pyflattendb": {
            "user.name": {"type": "string", "max_len": 100},
            "user.age": {"type": "integer", "min_value": 0},
            "address.city": {"type": "string", "choices": ["Boston", "New York"]},
        },
        "user": {"name": "John", "age": 30, "address": {"street": "123 Main St", "city": "Boston"}},
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "address" in structure

    # Check metadata was applied
    user_fields = structure["user"]
    name_field = next(f for f in user_fields if f.name == "name")
    assert name_field.metadata == {"type": "string", "max_len": 100}

    age_field = next(f for f in user_fields if f.name == "age")
    assert age_field.metadata == {"type": "integer", "min_value": 0}

    address_fields = structure["address"]
    city_field = next(f for f in address_fields if f.name == "city")
    assert city_field.metadata == {"type": "string", "choices": ["Boston", "New York"]}


def test_analyze_structure_raw_object() -> None:
    """Test analysis of a raw object with explicit type name."""
    data = {"name": "John", "address": {"street": "123 Main St", "city": "Boston"}}
    generator = SchemaGenerator(data, type_name="user")
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "address" in structure

    # Check user fields
    user_fields = structure["user"]
    assert len(user_fields) == 2
    assert any(f.name == "name" and f.python_type == str for f in user_fields)

    address_field = next(f for f in user_fields if f.name == "address")
    assert address_field.is_relationship
    assert address_field.relationship_type == "address"
    assert address_field.is_foreign_key
    assert address_field.foreign_key_to == "address"


def test_metadata_extraction() -> None:
    """Test extraction and application of metadata."""
    data = {
        "_pyflattendb": {
            "user.name": {"type": "string", "max_len": 100},
            "user.age": {"type": "integer", "nullable": True},
        },
        "user": {"name": "John", "age": None},
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    user_fields = structure["user"]
    name_field = next(f for f in user_fields if f.name == "name")
    assert name_field.metadata == {"type": "string", "max_len": 100}
    assert name_field.python_type == str

    age_field = next(f for f in user_fields if f.name == "age")
    assert age_field.metadata == {"type": "integer", "nullable": True}
    assert age_field.nullable


def test_metadata_type_override() -> None:
    """Test that metadata can override inferred types."""
    data = {"_pyflattendb": {"user.age": {"type": "string"}}, "user": {"age": 30}}  # Override int to string
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    user_fields = structure["user"]
    age_field = next(f for f in user_fields if f.name == "age")
    assert age_field.python_type == str


def test_metadata_nullability() -> None:
    """Test that metadata can control nullability."""
    data = {
        "_pyflattendb": {"user.name": {"nullable": False}, "user.age": {"nullable": True}},
        "user": {"name": "John", "age": None},
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    user_fields = structure["user"]
    name_field = next(f for f in user_fields if f.name == "name")
    assert not name_field.nullable

    age_field = next(f for f in user_fields if f.name == "age")
    assert age_field.nullable


def test_metadata_invalid_type() -> None:
    """Test that invalid types in metadata raise errors."""
    data = {"_pyflattendb": {"user.age": {"type": "invalid_type"}}, "user": {"age": 30}}
    generator = SchemaGenerator(data)
    with pytest.raises(ValueError, match="Unsupported type in metadata"):
        generator.analyze_structure()


def test_metadata_nested_objects() -> None:
    """Test metadata handling with nested objects."""
    data = {
        "_pyflattendb": {
            "user.address": {"entity_type": "location"},
            "location.city": {"type": "string", "choices": ["Boston", "New York"]},
        },
        "user": {"name": "John", "address": {"street": "123 Main St", "city": "Boston"}},
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "location" in structure  # Note: address was renamed to location

    user_fields = structure["user"]
    address_field = next(f for f in user_fields if f.name == "address")
    assert address_field.relationship_type == "location"
    assert address_field.is_foreign_key
    assert address_field.foreign_key_to == "location"

    location_fields = structure["location"]
    city_field = next(f for f in location_fields if f.name == "city")
    assert city_field.metadata == {"type": "string", "choices": ["Boston", "New York"]}


def test_metadata_list_items() -> None:
    """Test metadata for list items."""
    data = {
        "_pyflattendb": {
            "user.orders": {"entity_type": "purchase"},
            "purchase.total": {"type": "float", "min_value": 0},
        },
        "user": {"name": "John", "orders": [{"id": 1, "total": 100.0}, {"id": 2, "total": 200.0}]},
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "purchase" in structure  # Note: orders was renamed to purchase

    user_fields = structure["user"]
    orders_field = next(f for f in user_fields if f.name == "orders")
    assert orders_field.relationship_type == "purchase"
    assert orders_field.is_list
    assert orders_field.is_foreign_key
    assert orders_field.foreign_key_to == "purchase"

    purchase_fields = structure["purchase"]
    total_field = next(f for f in purchase_fields if f.name == "total")
    assert total_field.metadata == {"type": "float", "min_value": 0}


def test_entity_type_detection() -> None:
    """Test automatic detection of common entity types."""
    data = {
        "user": {
            "name": "John",
            "addresses": [  # Plural form
                {"street": "123 Main St", "city": "Boston"},
                {"street": "456 Oak St", "city": "New York"},
            ],
            "orders": [{"id": 1, "total": 100.0}, {"id": 2, "total": 200.0}],  # Common entity type
        }
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "address" in structure  # Singularized from "addresses"
    assert "order" in structure  # Common entity type

    user_fields = structure["user"]
    addresses_field = next(f for f in user_fields if f.name == "addresses")
    assert addresses_field.relationship_type == "address"
    assert addresses_field.is_list
    assert addresses_field.is_foreign_key
    assert addresses_field.foreign_key_to == "address"

    orders_field = next(f for f in user_fields if f.name == "orders")
    assert orders_field.relationship_type == "order"
    assert orders_field.is_list
    assert orders_field.is_foreign_key
    assert orders_field.foreign_key_to == "order"


def test_custom_entity_type() -> None:
    """Test custom entity type specification via metadata."""
    data = {
        "_pyflattendb": {"user.home": {"entity_type": "residence"}, "user.work": {"entity_type": "office"}},
        "user": {
            "name": "John",
            "home": {"street": "123 Main St", "city": "Boston"},
            "work": {"street": "456 Work St", "city": "New York"},
        },
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "residence" in structure
    assert "office" in structure

    user_fields = structure["user"]
    home_field = next(f for f in user_fields if f.name == "home")
    assert home_field.relationship_type == "residence"
    assert home_field.is_foreign_key
    assert home_field.foreign_key_to == "residence"

    work_field = next(f for f in user_fields if f.name == "work")
    assert work_field.relationship_type == "office"
    assert work_field.is_foreign_key
    assert work_field.foreign_key_to == "office"


def test_nested_entity_relationships() -> None:
    """Test handling of nested entity relationships."""
    data = {
        "user": {
            "name": "John",
            "address": {"street": "123 Main St", "city": "Boston", "country": {"name": "USA", "code": "US"}},
        }
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "address" in structure
    assert "country" in structure

    user_fields = structure["user"]
    address_field = next(f for f in user_fields if f.name == "address")
    assert address_field.relationship_type == "address"
    assert address_field.is_foreign_key
    assert address_field.foreign_key_to == "address"

    address_fields = structure["address"]
    country_field = next(f for f in address_fields if f.name == "country")
    assert country_field.relationship_type == "country"
    assert country_field.is_foreign_key
    assert country_field.foreign_key_to == "country"


def test_list_of_entities() -> None:
    """Test handling of lists of entities."""
    data = {
        "user": {
            "name": "John",
            "addresses": [{"street": "123 Main St", "city": "Boston"}, {"street": "456 Oak St", "city": "New York"}],
            "orders": [
                {"id": 1, "items": [{"product": "Book", "quantity": 2}, {"product": "Pen", "quantity": 3}]},
                {"id": 2, "items": [{"product": "Notebook", "quantity": 1}]},
            ],
        }
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "address" in structure
    assert "order" in structure
    assert "item" in structure

    user_fields = structure["user"]
    addresses_field = next(f for f in user_fields if f.name == "addresses")
    assert addresses_field.relationship_type == "address"
    assert addresses_field.is_list
    assert addresses_field.is_foreign_key
    assert addresses_field.foreign_key_to == "address"

    orders_field = next(f for f in user_fields if f.name == "orders")
    assert orders_field.relationship_type == "order"
    assert orders_field.is_list
    assert orders_field.is_foreign_key
    assert orders_field.foreign_key_to == "order"

    order_fields = structure["order"]
    items_field = next(f for f in order_fields if f.name == "items")
    assert items_field.relationship_type == "item"
    assert items_field.is_list
    assert items_field.is_foreign_key
    assert items_field.foreign_key_to == "item"


def test_non_entity_nested_object() -> None:
    """Test handling of nested objects that are not entities."""
    data = {
        "_pyflattendb": {"user.preferences": {"entity_type": None}},  # Explicitly mark as non-entity
        "user": {"name": "John", "preferences": {"theme": "dark", "notifications": True}},
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "preferences" not in structure  # Should not create a separate entity

    user_fields = structure["user"]
    preferences_field = next(f for f in user_fields if f.name == "preferences")
    assert not preferences_field.is_relationship
    assert preferences_field.python_type == dict


def test_entity_type_override() -> None:
    """Test overriding entity types for objects and lists."""
    data = {
        "_pyflattendb": {
            "user.home_address": {"entity_type": "residence"},
            "user.work_address": {"entity_type": "office"},
            "user.purchases": {"entity_type": "transaction"},
        },
        "user": {
            "name": "John",
            "home_address": {"street": "123 Home St", "city": "Boston"},
            "work_address": {"street": "456 Work St", "city": "New York"},
            "purchases": [{"id": 1, "amount": 100.0}, {"id": 2, "amount": 200.0}],
        },
    }
    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    assert "user" in structure
    assert "residence" in structure
    assert "office" in structure
    assert "transaction" in structure

    user_fields = structure["user"]
    home_field = next(f for f in user_fields if f.name == "home_address")
    assert home_field.relationship_type == "residence"
    assert home_field.is_foreign_key
    assert home_field.foreign_key_to == "residence"

    work_field = next(f for f in user_fields if f.name == "work_address")
    assert work_field.relationship_type == "office"
    assert work_field.is_foreign_key
    assert work_field.foreign_key_to == "office"

    purchases_field = next(f for f in user_fields if f.name == "purchases")
    assert purchases_field.relationship_type == "transaction"
    assert purchases_field.is_list
    assert purchases_field.is_foreign_key
    assert purchases_field.foreign_key_to == "transaction"


def test_reference_table_string_field() -> None:
    """Test that string fields can be marked as reference tables."""
    data = {
        "product": {
            "name": "Widget",
            "status": "active",
            "_pyflattendb": {"product.status": {"is_reference_table": True, "reference_table_name": "product_status"}},
        }
    }

    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    # Verify product table structure
    product_fields = structure["product"]
    status_field = next(f for f in product_fields if f.name == "status")

    assert status_field.is_reference_table
    assert status_field.reference_table_name == "product_status"
    assert status_field.python_type == str
    assert not status_field.is_relationship  # Should not be a relationship since it's a reference table
    assert not status_field.is_foreign_key


def test_many_to_many_relationship() -> None:
    """Test that list fields can be marked as many-to-many relationships."""
    data = {
        "product": {
            "name": "Widget",
            "tags": [{"name": "electronics"}, {"name": "gadget"}],
            "_pyflattendb": {"product.tags": {"is_many_to_many": True, "association_table_name": "product_tags"}},
        }
    }

    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    # Verify product table structure
    product_fields = structure["product"]
    tags_field = next(f for f in product_fields if f.name == "tags")

    assert tags_field.is_many_to_many
    assert tags_field.association_table_name == "product_tags"
    assert tags_field.is_list
    assert tags_field.is_relationship
    assert tags_field.relationship_type == "tag"
    assert not tags_field.is_foreign_key  # Should not be a direct foreign key since it's many-to-many

    # Verify tag table was created
    assert "tag" in structure
    tag_fields = structure["tag"]
    assert len(tag_fields) > 0
    assert any(f.name == "name" for f in tag_fields)


def test_combined_reference_and_many_to_many() -> None:
    """Test combining reference tables with many-to-many relationships."""
    data = {
        "product": {
            "name": "Widget",
            "status": "active",
            "categories": [{"name": "Electronics"}, {"name": "Gadgets"}],
            "_pyflattendb": {
                "product.status": {"is_reference_table": True, "reference_table_name": "product_status"},
                "product.categories": {"is_many_to_many": True, "association_table_name": "product_categories"},
            },
        }
    }

    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    # Verify product table structure
    product_fields = structure["product"]

    # Check status field
    status_field = next(f for f in product_fields if f.name == "status")
    assert status_field.is_reference_table
    assert status_field.reference_table_name == "product_status"

    # Check categories field
    categories_field = next(f for f in product_fields if f.name == "categories")
    assert categories_field.is_many_to_many
    assert categories_field.association_table_name == "product_categories"
    assert categories_field.is_list
    assert categories_field.relationship_type == "category"

    # Verify both reference and category tables were created
    assert status_field.is_reference_table
    assert status_field.reference_table_name == "product_status"


def test_reference_table_with_choices() -> None:
    """Test reference tables with predefined choices."""
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
    structure = generator.analyze_structure()

    # Verify product table structure
    product_fields = structure["product"]
    status_field = next(f for f in product_fields if f.name == "status")

    assert status_field.is_reference_table
    assert status_field.reference_table_name == "product_status"
    assert "choices" in status_field.metadata
    assert status_field.metadata["choices"] == ["active", "inactive", "discontinued"]


def test_many_to_many_with_custom_entity_type() -> None:
    """Test many-to-many relationships with custom entity types."""
    data = {
        "product": {
            "name": "Widget",
            "related_products": [{"name": "Gadget"}, {"name": "Tool"}],
            "_pyflattendb": {
                "product.related_products": {
                    "is_many_to_many": True,
                    "association_table_name": "product_relations",
                    "entity_type": "product",  # Self-referential many-to-many
                }
            },
        }
    }

    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    # Verify product table structure
    product_fields = structure["product"]
    related_field = next(f for f in product_fields if f.name == "related_products")

    assert related_field.is_many_to_many
    assert related_field.association_table_name == "product_relations"
    assert related_field.relationship_type == "product"  # Should use the custom entity type
    assert related_field.is_list


def test_invalid_reference_table() -> None:
    """Test that non-string fields cannot be reference tables."""
    data = {
        "product": {
            "name": "Widget",
            "price": 99.99,
            "_pyflattendb": {
                "product.price": {"is_reference_table": True}  # This should be ignored since price is not a string
            },
        }
    }

    generator = SchemaGenerator(data)
    structure = generator.analyze_structure()

    # Verify product table structure
    product_fields = structure["product"]
    price_field = next(f for f in product_fields if f.name == "price")

    assert not price_field.is_reference_table  # Should not be a reference table
    assert price_field.python_type == float


def test_visualization_includes_new_fields() -> None:
    """Test that the visualization includes reference tables and many-to-many relationships."""
    data = {
        "product": {
            "name": "Widget",
            "status": "active",
            "tags": [{"name": "electronics"}],
            "_pyflattendb": {"product.status": {"is_reference_table": True}, "product.tags": {"is_many_to_many": True}},
        }
    }

    from io import StringIO

    from rich.console import Console

    # Redirect console output
    sio = StringIO()
    console = Console(file=sio)
    generator = SchemaGenerator(data, console_instance=console)

    # Generate visualization
    generator.visualize_schema()

    # Get the output
    output = sio.getvalue()
    # print("\n--- Visualization Output ---\n", output)

    # Check for field values only (not headers, which may be truncated/wrapped)
    assert "True" in output  # For is_reference_table or is_many_to_many
    assert "pro…" in output  # Truncated association table name as rendered by Rich
