# PyFlattenDB

A Python library that automatically generates SQLAlchemy and Pydantic models from arbitrary Python objects. PyFlattenDB analyzes your data structures and creates corresponding database schemas and validation models, making it easy to work with complex, nested data in both database and API contexts.

## Features

- **Automatic Schema Generation**: Convert Python objects into SQLAlchemy and Pydantic models
- **Complex Data Support**: Handle nested objects, relationships, and various field types
- **Relationship Management**: Support for one-to-one, one-to-many, and many-to-many relationships
- **Reference Tables**: Create enumerated value tables for string fields
- **Rich Metadata**: Fine-grained control over field properties and relationships
- **Schema Visualization**: Pretty-ish console output for schema inspection
- **Type Inference**: Smart detection of entity types and relationships
- **Custom Validation**: Support for field constraints, patterns, and custom validators

## Quick Start

```python
from pyflattendb import SchemaGenerator

# Define your data structure
data = {
    "user": {
        "name": "John Doe",
        "age": 30,
        "email": "john@example.com",
        "address": {
            "street": "123 Main St",
            "city": "Boston",
            "zip": "02108"
        },
        "orders": [
            {
                "id": 1,
                "items": [
                    {"product": "Book", "quantity": 2},
                    {"product": "Pen", "quantity": 3}
                ]
            }
        ]
    }
}

# Generate models
generator = SchemaGenerator(data)
sqlalchemy_models = generator.generate_sqlalchemy_models()
pydantic_models = generator.generate_pydantic_models()

# Visualize the schema
generator.visualize_schema()
```

## Advanced Usage

### Metadata and Field Options

You can customize field behavior using metadata:

```python
data = {
    "product": {
        "name": "Widget",
        "price": 99.99,
        "status": "active",
        "_pyflattendb": {
            "product.name": {
                "max_len": 100,
                "nullable": False,
                "description": "Product name"
            },
            "product.status": {
                "is_reference_table": True,
                "choices": ["active", "inactive", "discontinued"]
            }
        }
    }
}
```

### Relationship Types

#### One-to-One
```python
data = {
    "user": {
        "name": "John",
        "profile": {
            "bio": "Software developer",
            "website": "https://example.com"
        }
    }
}
```

#### One-to-Many
```python
data = {
    "user": {
        "name": "John",
        "orders": [
            {"id": 1, "total": 100.0},
            {"id": 2, "total": 200.0}
        ]
    }
}
```

#### Many-to-Many
```python
data = {
    "product": {
        "name": "Widget",
        "categories": [
            {"name": "Electronics"},
            {"name": "Gadgets"}
        ],
        "_pyflattendb": {
            "product.categories": {
                "is_many_to_many": True
            }
        }
    }
}
```

### Reference Tables

Create enumerated value tables for string fields:

```python
data = {
    "order": {
        "status": "pending",
        "_pyflattendb": {
            "order.status": {
                "is_reference_table": True,
                "choices": ["pending", "processing", "completed", "cancelled"]
            }
        }
    }
}
```

## Field Metadata Options

The following metadata options are available for fields:

| Option | Type | Description |
|--------|------|-------------|
| `type` | str | Override the inferred type |
| `max_len` | int | Maximum length for string fields |
| `min_len` | int | Minimum length for string fields |
| `nullable` | bool | Override field nullability |
| `unique` | bool | Make field unique |
| `primary_key` | bool | Make field a primary key |
| `foreign_key` | str | Specify foreign key relationship |
| `description` | str | Field description |
| `default` | Any | Default value |
| `choices` | List[Any] | List of allowed values |
| `regex` | str | Regular expression pattern |
| `min_value` | Union[int, float] | Minimum value for numeric fields |
| `max_value` | Union[int, float] | Maximum value for numeric fields |
| `precision` | int | Decimal precision |
| `scale` | int | Decimal scale |
| `entity_type` | str | Specify entity type for nested object |
| `is_reference_table` | bool | Mark as reference table |
| `reference_table_name` | str | Custom reference table name |
| `is_many_to_many` | bool | Mark as many-to-many relationship |
| `association_table_name` | str | Custom association table name |

## Demo Output

> poetry run python demo.py
<pre>
╭────────────────────────────── PyFlattenDB Demo ──────────────────────────────╮
│ This demo showcases PyFlattenDB's ability to handle complex data structures: │
│ • Nested objects (store → address, departments → manager)                    │
│ • One-to-many relationships (store → products, store → orders)               │
│ • Many-to-many relationships (products ↔ categories)                         │
│ • Reference tables (status fields, payment methods)                          │
│ • Custom metadata and validations                                            │
│ • Debug logging (use --debug flag to enable)                                 │
╰──────────────────────────────────────────────────────────────────────────────╯

Initializing SchemaGenerator...

Analyzing data structure...

Generating SQLAlchemy models...
Generated 13 SQLAlchemy models

Generating Pydantic models...
Generated 11 Pydantic models

Schema Visualization:
                                                                  Schema Structure: address
┏━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field   ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id      │ int  │ False    │ True        │              │ False   │ False │       │ False        │                │ False  │             │ primary_key=True │
│ street  │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ city    │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ state   │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ zip     │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ country │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
└─────────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴───────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                                 Schema Structure: manager
┏━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id    │ int  │ False    │ True        │              │ False   │ False │       │ False        │                │ False  │             │ primary_key=True │
│ name  │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ email │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ role  │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
└───────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴───────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                                   Schema Structure: department
┏━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field      ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To   ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id         │ int  │ False    │ True        │              │ False   │ False │         │ False        │                │ False  │             │ primary_key=True │
│ name       │ str  │ False    │ False       │              │ False   │ False │         │ False        │                │ False  │             │                  │
│ manager_id │ int  │ False    │ False       │ manager      │ False   │ True  │ manager │ False        │                │ False  │             │                  │
└────────────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴─────────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                                 Schema Structure: category
┏━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id    │ int  │ False    │ True        │              │ False   │ False │       │ False        │                │ False  │             │ primary_key=True │
│ name  │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
└───────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴───────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                               Schema Structure: specifications
┏━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field    ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id       │ int  │ False    │ True        │              │ False   │ False │       │ False        │                │ False  │             │ primary_key=True │
│ color    │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ storage  │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ warranty │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
└──────────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴───────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                                                                Schema Structure: product
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field             ┃ Type  ┃ Nullable ┃ Primary Key ┃ Relationship   ┃ Is List ┃ Is FK ┃ FK To          ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table                  ┃ Metadata                             ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                │ int   │ False    │ True        │                │ False   │ False │                │ False        │                │ False  │                              │ primary_key=True                     │
│ name              │ str   │ False    │ False       │                │ False   │ False │                │ False        │                │ False  │                              │                                      │
│ sku               │ str   │ False    │ False       │                │ False   │ False │                │ False        │                │ False  │                              │                                      │
│ price             │ float │ False    │ False       │                │ False   │ False │                │ False        │                │ False  │                              │                                      │
│ status            │ str   │ False    │ False       │                │ False   │ False │                │ True         │ status_ref     │ False  │                              │ is_reference_table=True,             │
│                   │       │          │             │                │         │       │                │              │                │        │                              │ choices=['in_stock', 'low_stock',    │
│                   │       │          │             │                │         │       │                │              │                │        │                              │ 'out_of_stock', 'discontinued'],     │
│                   │       │          │             │                │         │       │                │              │                │        │                              │ description=Current product          │
│                   │       │          │             │                │         │       │                │              │                │        │                              │ availability status                  │
│ categories        │ list  │ False    │ False       │ category       │ True    │ False │                │ False        │                │ True   │ product_category_association │ is_many_to_many=True,                │
│                   │       │          │             │                │         │       │                │              │                │        │                              │ description=Product categories       │
│ specifications_id │ int   │ False    │ False       │ specifications │ False   │ True  │ specifications │ False        │                │ False  │                              │                                      │
└───────────────────┴───────┴──────────┴─────────────┴────────────────┴─────────┴───────┴────────────────┴──────────────┴────────────────┴────────┴──────────────────────────────┴──────────────────────────────────────┘

                                                                 Schema Structure: customer
┏━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id    │ int  │ False    │ True        │              │ False   │ False │       │ False        │                │ False  │             │ primary_key=True │
│ name  │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ email │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ phone │ str  │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
└───────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴───────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                                     Schema Structure: item
┏━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field    ┃ Type  ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id       │ int   │ False    │ True        │              │ False   │ False │       │ False        │                │ False  │             │ primary_key=True │
│ product  │ str   │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ quantity │ int   │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ price    │ float │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
└──────────┴───────┴──────────┴─────────────┴──────────────┴─────────┴───────┴───────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                                  Schema Structure: payment
┏━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field  ┃ Type  ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata         ┃
┡━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ id     │ int   │ False    │ True        │              │ False   │ False │       │ False        │                │ False  │             │ primary_key=True │
│ method │ str   │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ status │ str   │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
│ amount │ float │ False    │ False       │              │ False   │ False │       │ False        │                │ False  │             │                  │
└────────┴───────┴──────────┴─────────────┴──────────────┴─────────┴───────┴───────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────┘

                                                                                                 Schema Structure: order
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field               ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To    ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata                                                     ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                  │ int  │ False    │ True        │              │ False   │ False │          │ False        │                │ False  │             │ primary_key=True                                             │
│ order_number        │ str  │ False    │ False       │              │ False   │ False │          │ False        │                │ False  │             │                                                              │
│ status              │ str  │ False    │ False       │              │ False   │ False │          │ True         │ status_ref     │ False  │             │ is_reference_table=True, choices=['pending', 'processing',   │
│                     │      │          │             │              │         │       │          │              │                │        │             │ 'shipped', 'delivered', 'cancelled'], description=Current    │
│                     │      │          │             │              │         │       │          │              │                │        │             │ order status                                                 │
│ customer_id         │ int  │ False    │ False       │ customer     │ False   │ True  │ customer │ False        │                │ False  │             │                                                              │
│ items               │ list │ False    │ False       │ item         │ True    │ True  │ item     │ False        │                │ False  │             │                                                              │
│ shipping_address_id │ int  │ False    │ False       │ address      │ False   │ True  │ address  │ False        │                │ False  │             │ description=Order shipping address, entity_type=address      │
│ payment_id          │ int  │ False    │ False       │ payment      │ False   │ True  │ payment  │ False        │                │ False  │             │                                                              │
└─────────────────────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴──────────┴──────────────┴────────────────┴────────┴─────────────┴──────────────────────────────────────────────────────────────┘

                                                                                                 Schema Structure: store
┏━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field       ┃ Type ┃ Nullable ┃ Primary Key ┃ Relationship ┃ Is List ┃ Is FK ┃ FK To      ┃ Is Ref Table ┃ Ref Table Name ┃ Is M2M ┃ Assoc Table ┃ Metadata                                                           ┃
┡━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id          │ int  │ False    │ True        │              │ False   │ False │            │ False        │                │ False  │             │ primary_key=True                                                   │
│ name        │ str  │ False    │ False       │              │ False   │ False │            │ False        │                │ False  │             │                                                                    │
│ website     │ str  │ False    │ False       │              │ False   │ False │            │ False        │                │ False  │             │                                                                    │
│ status      │ str  │ False    │ False       │              │ False   │ False │            │ True         │ status_ref     │ False  │             │ is_reference_table=True, choices=['active', 'inactive',            │
│             │      │          │             │              │         │       │            │              │                │        │             │ 'maintenance'], description=Current store status                   │
│ address_id  │ int  │ False    │ False       │ address      │ False   │ True  │ address    │ False        │                │ False  │             │ description=Store's physical address, entity_type=address          │
│ departments │ list │ False    │ False       │ department   │ True    │ True  │ department │ False        │                │ False  │             │                                                                    │
│ products    │ list │ False    │ False       │ product      │ True    │ True  │ product    │ False        │                │ False  │             │                                                                    │
│ orders      │ list │ False    │ False       │ order        │ True    │ True  │ order      │ False        │                │ False  │             │                                                                    │
└─────────────┴──────┴──────────┴─────────────┴──────────────┴─────────┴───────┴────────────┴──────────────┴────────────────┴────────┴─────────────┴────────────────────────────────────────────────────────────────────┘


Example Usage:

    # Using the generated SQLAlchemy models:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine('sqlite:///store.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create a new store
    store = Store(
        name="TechGadgets",
        status="active",
        address=Address(
            street="123 Tech Street",
            city="Silicon Valley",
            state="CA"
        )
    )
    session.add(store)
    session.commit()

    # Using the generated Pydantic models:
    from pydantic import BaseModel

    # Validate and serialize data
    store_data = {
        "name": "TechGadgets",
        "status": "active",
        "address": {
            "street": "123 Tech Street",
            "city": "Silicon Valley"
        }
    }
    store_model = StoreModel(**store_data)

    # Enable debug logging:
    import logging
    logging.getLogger('pyflattendb').setLevel(logging.DEBUG)
</pre>

## Development

### Setup

1. Clone the repository:
```bash
git clone https://github.com/random-things/pyflattendb.git
cd pyflattendb
```

2. Install dependencies:
```bash
poetry install
```

3. Set up pre-commit hooks:
```bash
poetry run pre-commit install
```

### Testing

Run the test suite:
```bash
poetry run pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [Rich](https://github.com/Textualize/rich) for beautiful console output
