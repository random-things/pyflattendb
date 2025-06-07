"""Core schema generation functionality for PyFlattenDB.

This module provides the core functionality for analyzing Python objects and generating
corresponding SQLAlchemy and Pydantic models. It handles complex data structures including
nested objects, relationships, and various field types.

The main class SchemaGenerator takes a Python object and generates:
1. SQLAlchemy models for database storage
2. Pydantic models for data validation and serialization

The generator supports:
- Complex nested structures
- One-to-one, one-to-many, and many-to-many relationships
- Custom field types and validations
- Reference tables for enumerated values
- Rich metadata for fine-grained control

Example:
    ```python
    from pyflattendb import SchemaGenerator

    data = {
        "user": {
            "name": "John Doe",
            "address": {
                "street": "123 Main St",
                "city": "Boston"
            }
        }
    }
    generator = SchemaGenerator(data)
    sqlalchemy_models = generator.generate_sqlalchemy_models()
    pydantic_models = generator.generate_pydantic_models()
    ```
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Self, Set, Type, TypedDict

from pydantic import BaseModel
from pydantic import Field as PydanticField
from pydantic import create_model
from rich.console import Console
from rich.table import Table as RichTable
from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Integer, MetaData, String, Table, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Default to INFO level

# Create console handler if no handlers exist
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

console = Console()


class FieldMetadata(TypedDict, total=False):
    """Type definition for field metadata options.

    This TypedDict defines all possible metadata options that can be specified for a field
    in the input data structure. These options control how the field is interpreted and
    generated in both SQLAlchemy and Pydantic models.

    Attributes:
        type: Override the inferred type with a specific type name.
        max_len: Maximum length for string fields.
        min_len: Minimum length for string fields.
        nullable: Override the default nullability of the field.
        unique: Make the field unique in the database.
        primary_key: Make the field a primary key.
        foreign_key: Specify a foreign key relationship.
        description: Field description for documentation.
        default: Default value for the field.
        choices: List of allowed values for the field.
        regex: Regular expression pattern for validation.
        min_value: Minimum value for numeric fields.
        max_value: Maximum value for numeric fields.
        precision: Decimal precision for numeric fields.
        scale: Decimal scale for numeric fields.
        entity_type: Specify the entity type for a nested object.
        is_reference_table: Mark field as a reference table (string enum).
        reference_table_name: Name for the reference table if different from field name.
        is_many_to_many: Mark field as a many-to-many relationship.
        association_table_name: Name for the association table if different from default.
    """


@dataclass
class FieldInfo:
    """Information about a field in the schema."""

    name: str
    python_type: Type
    nullable: bool
    is_relationship: bool = False
    relationship_type: Optional[str] = None
    is_list: bool = False
    description: Optional[str] = None
    metadata: FieldMetadata = field(default_factory=dict)
    is_foreign_key: bool = False
    foreign_key_to: Optional[str] = None
    is_reference_table: bool = False  # Whether this field should be a reference table
    reference_table_name: Optional[str] = None  # Name of the reference table if different from field name
    is_many_to_many: bool = False  # Whether this is a many-to-many relationship
    association_table_name: Optional[str] = None  # Name of the association table if different from default


class SchemaGenerator:
    """Generates SQLAlchemy and Pydantic schemas from Python objects.

    This class is the main entry point for schema generation. It takes a Python object
    structure and generates corresponding SQLAlchemy and Pydantic models. The generator
    analyzes the structure recursively, handling nested objects, relationships, and
    various field types.

    The generator supports several types of relationships:
    - One-to-one: Direct foreign key relationships
    - One-to-many: List of related objects
    - Many-to-many: Using association tables
    - Reference tables: For enumerated string values

    Attributes:
        METADATA_KEY: Key used to store metadata in the input data structure.
        COMMON_ENTITIES: Set of common entity names used for type inference.

    Example:
        ```python
        data = {
            "user": {
                "name": "John",
                "address": {
                    "street": "123 Main St",
                    "city": "Boston"
                },
                "orders": [
                    {"id": 1, "total": 100.0}
                ]
            }
        }
        generator = SchemaGenerator(data)
        sqlalchemy_models = generator.generate_sqlalchemy_models()
        pydantic_models = generator.generate_pydantic_models()
        ```
    """

    METADATA_KEY = "_pyflattendb"
    COMMON_ENTITIES = {
        "address",
        "user",
        "order",
        "product",
        "customer",
        "employee",
        "company",
        "department",
        "location",
        "contact",
        "payment",
        "item",
    }

    def __init__(
        self: Self,
        data: Any,
        type_name: Optional[str] = None,
        _analyzed_structure: Optional[Dict[str, List[FieldInfo]]] = None,
        _metadata: Optional[Dict[str, FieldMetadata]] = None,
        console_instance: Optional[Console] = None,
    ) -> None:
        """Initialize the schema generator with input data.

        Args:
            data: The Python object to analyze and generate schemas for. Must be a dictionary.
            type_name: Optional name for the type if data is a raw object without a top-level key.
                      If not provided and data is a dict with a single key, that key will be used.
            _analyzed_structure: Internal use for recursion, pass the current analyzed structure dict.
            _metadata: Optional metadata dictionary to use instead of extracting from data.
            console_instance: Optional console instance to use for visualization.

        Raises:
            ValueError: If data is not a dictionary or if type_name is not provided and data
                      has multiple top-level keys.
        """
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")

        # Extract metadata first
        if _metadata is not None:
            self._metadata = _metadata
        else:
            self._metadata = self._extract_metadata(data)

        # Remove metadata from data
        if self.METADATA_KEY in data:
            data = {k: v for k, v in data.items() if k != self.METADATA_KEY}

        # Set type name and root data
        if type_name is not None:
            self.type_name = type_name
            self._root_data = data if type_name not in data else data[type_name]
        elif len(data) == 1:
            self.type_name = next(iter(data))
            self._root_data = data[self.type_name]
        else:
            raise ValueError("Either provide a type_name or ensure data is a dict with a single key")
        self.data = data
        self._type_mapping = {
            str: String,
            int: Integer,
            float: Float,
            bool: Boolean,
            dict: JSON,
            list: JSON,  # For now, store lists as JSON. Could be expanded to use ARRAY type
            # Add more type mappings as needed
        }
        if _analyzed_structure is not None:
            self._analyzed_structure = _analyzed_structure
        else:
            self._analyzed_structure: Dict[str, List[FieldInfo]] = {}
        self._entity_types: Set[str] = set()  # Track all entity types we've seen
        self.console = console_instance or console

    def _singularize(self: Self, word: str) -> str:
        """Convert a plural word to singular form.

        This method handles both regular and irregular plurals. It's used to normalize
        entity names and relationship types.

        Args:
            word: The word to convert to singular form.

        Returns:
            The singular form of the word, or the original word if no conversion is needed.

        Example:
            >>> generator._singularize("addresses")
            'address'
            >>> generator._singularize("children")
            'child'
            >>> generator._singularize("users")
            'user'
        """
        if not word or not isinstance(word, str):
            return word
        # Common irregular plurals
        irregulars = {
            "addresses": "address",
            "children": "child",
            "feet": "foot",
            "geese": "goose",
            "men": "man",
            "mice": "mouse",
            "people": "person",
            "teeth": "tooth",
            "women": "woman",
            "items": "item",
        }

        if word in irregulars:
            return irregulars[word]

        # Regular plural rules
        if word.endswith("ies"):
            return word[:-3] + "y"
        if word.endswith("es"):
            return word[:-2]
        if word.endswith("s"):
            return word[:-1]

        return word

    def _determine_entity_type(self: Self, value: Dict[str, Any], field_name: str, parent_type: str) -> str:
        """Determine the entity type for a nested object.

        This method analyzes a nested object to determine its entity type. It uses several
        strategies in order:
        1. Check for explicit entity_type in metadata
        2. Try singularizing the field name
        3. Check if the field name is a common entity
        4. Use the field name as is

        Args:
            value: The nested object to analyze.
            field_name: The name of the field containing this object.
            parent_type: The type name of the parent object.

        Returns:
            The determined entity type name.

        Example:
            >>> data = {"user": {"address": {"street": "123 Main St"}}}
            >>> generator = SchemaGenerator(data)
            >>> generator._determine_entity_type({"street": "123 Main St"}, "address", "user")
            'address'
        """
        # Check if there's an explicit entity type in metadata
        metadata = self._get_field_metadata(parent_type, field_name)
        if "entity_type" in metadata:
            logger.debug(
                "_determine_entity_type: field_name=%s, parent_type=%s, entity_type(from metadata)=%s",
                field_name,
                parent_type,
                metadata["entity_type"],
            )
            return metadata["entity_type"]
        # Try singularizing the field name
        singular_name = self._singularize(field_name.lower())
        if singular_name in self.COMMON_ENTITIES:
            logger.debug(
                "_determine_entity_type: field_name=%s, parent_type=%s, entity_type(singular)=%s",
                field_name,
                parent_type,
                singular_name,
            )
            return singular_name
        if field_name.lower() in self.COMMON_ENTITIES:
            logger.debug(
                "_determine_entity_type: field_name=%s, parent_type=%s, entity_type(direct)=%s",
                field_name,
                parent_type,
                field_name.lower(),
            )
            return field_name.lower()
        logger.debug(
            "_determine_entity_type: field_name=%s, parent_type=%s, entity_type(default)=%s",
            field_name,
            parent_type,
            field_name,
        )
        return field_name

    def _extract_metadata(self: Self, data: Dict[str, Any]) -> Dict[str, FieldMetadata]:
        """Extract metadata from the _pyflattendb key if present."""
        metadata = data.get(self.METADATA_KEY, {})
        if not isinstance(metadata, dict):
            return {}
        return metadata

    def _get_field_metadata(self: Self, type_name: str, field_name: str) -> FieldMetadata:
        """Get metadata for a specific field."""
        # Try with the original type name
        key = f"{type_name}.{field_name}"
        if key in self._metadata:
            logger.debug("_get_field_metadata: Found metadata for %s", key)
            return self._metadata[key]
        # Try with the singularized type name
        singular_type = self._singularize(type_name)
        if singular_type != type_name:
            key = f"{singular_type}.{field_name}"
            if key in self._metadata:
                logger.debug("_get_field_metadata: Found metadata for %s", key)
                return self._metadata[key]
        logger.debug("_get_field_metadata: No metadata found for %s.%s", type_name, field_name)
        return {}

    def _get_type_name(self: Self) -> str:
        """Get the type name from either the provided type_name or the data structure."""
        return self.type_name

    def _get_root_data(self: Self) -> Any:
        """Get the root data object to analyze."""
        return self._root_data

    def _analyze_value(self: Self, value: Any, field_name: str, parent_type: str) -> FieldInfo:
        # Get metadata for this field
        metadata = self._get_field_metadata(parent_type, field_name)
        logger.debug("_analyze_value: field_name=%s, parent_type=%s, metadata=%s", field_name, parent_type, metadata)

        # Handle reference tables (string enums)
        if metadata.get("is_reference_table", False) and isinstance(value, str):
            field_info = FieldInfo(
                name=field_name,
                python_type=str,
                nullable=metadata.get("nullable", value is None),
                description=metadata.get("description"),
                metadata=metadata,
                is_reference_table=True,
                reference_table_name=metadata.get("reference_table_name", f"{field_name}_ref"),
            )
            logger.debug("_analyze_value: Created reference table field_info=%s", field_info)
            return field_info

        # Handle explicit type override from metadata
        if "type" in metadata:
            type_map = {"string": str, "integer": int, "float": float, "boolean": bool, "json": dict, "array": list}
            python_type = type_map.get(metadata["type"])
            if python_type is None:
                raise ValueError(f"Unsupported type in metadata: {metadata['type']}")
        else:
            python_type = type(value) if value is not None else type(None)

        nullable = metadata.get("nullable", value is None)
        field_info = FieldInfo(
            name=field_name,
            python_type=python_type,
            nullable=nullable,
            description=metadata.get("description"),
            metadata=metadata,
        )

        if value is None:
            # If metadata specifies entity_type, treat as relationship
            if "entity_type" in metadata:
                entity_type = metadata["entity_type"]
                field_info.is_relationship = True
                field_info.relationship_type = entity_type
                field_info.python_type = Any
            return field_info
        if field_name == parent_type:
            return field_info

        # Handle relationships
        if isinstance(value, dict):
            entity_type = self._determine_entity_type(value, field_name, parent_type)
            logger.debug("_analyze_value (dict): field_name=%s, entity_type=%s", field_name, entity_type)
            if entity_type is not None:
                self._entity_types.add(entity_type)
                field_info.is_relationship = True
                field_info.relationship_type = entity_type
                field_info.is_foreign_key = True
                field_info.foreign_key_to = entity_type
                logger.debug("_analyze_value (dict): Updated field_info=%s", field_info)
            return field_info
        elif isinstance(value, list):
            field_info.is_list = True
            if not value:
                return field_info

            first_item = value[0]
            if isinstance(first_item, dict):
                # Use entity_type from metadata if present, else singularize field_name
                entity_type = metadata.get("entity_type") or self._singularize(field_name)
                logger.debug("_analyze_value (list): field_name=%s, entity_type=%s", field_name, entity_type)
                if entity_type is not None:
                    self._entity_types.add(entity_type)
                    field_info.is_relationship = True
                    field_info.relationship_type = entity_type

                    # Handle many-to-many relationships
                    if metadata.get("is_many_to_many", False):
                        field_info.is_many_to_many = True
                        field_info.association_table_name = metadata.get(
                            "association_table_name", f"{parent_type}_{entity_type}_association"
                        )
                        field_info.is_foreign_key = False  # Many-to-many uses association table instead
                    else:
                        field_info.is_foreign_key = True
                        field_info.foreign_key_to = entity_type

                    logger.debug("_analyze_value (list): Updated field_info=%s", field_info)
            return field_info
        return field_info

    def analyze_structure(self: Self) -> Dict[str, List[FieldInfo]]:
        """Analyze the structure of the input data and generate field information.

        This method performs a recursive analysis of the input data structure, generating
        FieldInfo objects for each field. It handles:
        - Basic field types (str, int, float, bool, etc.)
        - Nested objects and relationships
        - Lists of objects
        - Reference tables
        - Many-to-many relationships

        The analysis is performed in two passes:
        1. First pass: Analyze all fields and their types
        2. Second pass: Process relationships and nested structures

        Returns:
            A dictionary mapping type names to lists of FieldInfo objects.

        Example:
            ```python
            data = {
                "user": {
                    "name": "John",
                    "address": {"street": "123 Main St"}
                }
            }
            generator = SchemaGenerator(data)
            structure = generator.analyze_structure()
            # Returns: {
            #     "user": [FieldInfo(name="name", ...), FieldInfo(name="address", ...)],
            #     "address": [FieldInfo(name="street", ...)]
            # }
            ```
        """
        root_data = self._get_root_data()
        type_name = self._get_type_name()
        logger.debug("analyze_structure: Starting analysis for type_name=%s", type_name)

        # Extract metadata first
        if self.METADATA_KEY in root_data:
            metadata = root_data[self.METADATA_KEY]
            if isinstance(metadata, dict):
                self._metadata.update(metadata)
                logger.debug("analyze_structure: Updated metadata from root: %s", metadata)
            # Remove metadata from data to avoid processing it as a field
            root_data = {k: v for k, v in root_data.items() if k != self.METADATA_KEY}

        self._entity_types.add(type_name)
        if not isinstance(root_data, dict):
            raise ValueError("Root data must be a dictionary")

        fields: List[FieldInfo] = []
        for field_name, value in root_data.items():
            if field_name == self.METADATA_KEY:
                continue  # Skip metadata field

            entity_type = None
            if isinstance(value, dict):
                entity_type = self._determine_entity_type(value, field_name, type_name)
                logger.debug("analyze_structure: Processing dict field=%s, entity_type=%s", field_name, entity_type)
                field_info = self._analyze_value(value, field_name, type_name)
                logger.debug("analyze_structure: Created field_info=%s", field_info)
                fields.append(field_info)
                if field_info.is_relationship and not field_info.is_list and entity_type is not None:
                    logger.debug(
                        "analyze_structure: Recursively analyzing nested object field=%s, entity_type=%s",
                        field_name,
                        entity_type,
                    )
                    if entity_type not in self._analyzed_structure:
                        nested_data = {entity_type: value}
                        nested_generator = SchemaGenerator(
                            nested_data,
                            type_name=entity_type,
                            _analyzed_structure=self._analyzed_structure,
                            _metadata=self._metadata,
                            console_instance=self.console,
                        )
                        nested_structure = nested_generator.analyze_structure()
                        logger.debug(
                            "analyze_structure: Got nested structure for %s: %s", entity_type, nested_structure
                        )
                        self._analyzed_structure.update(nested_structure)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Use singularized field name for nested type
                field_metadata = self._get_field_metadata(type_name, field_name)
                entity_type = field_metadata.get("entity_type") or self._singularize(field_name)
                logger.debug("analyze_structure: Processing list field=%s, entity_type=%s", field_name, entity_type)
                field_info = self._analyze_value(value, field_name, type_name)
                logger.debug("analyze_structure: Created field_info=%s", field_info)
                fields.append(field_info)
                if field_info.is_relationship and field_info.is_list and value and entity_type is not None:
                    logger.debug(
                        "analyze_structure: Recursively analyzing list field=%s, entity_type=%s",
                        field_name,
                        entity_type,
                    )
                    if entity_type not in self._analyzed_structure:
                        nested_data = {entity_type: value[0]}
                        nested_generator = SchemaGenerator(
                            nested_data,
                            type_name=entity_type,
                            _analyzed_structure=self._analyzed_structure,
                            _metadata=self._metadata,
                            console_instance=self.console,
                        )
                        nested_structure = nested_generator.analyze_structure()
                        logger.debug(
                            "analyze_structure: Got nested structure for %s: %s", entity_type, nested_structure
                        )
                        self._analyzed_structure.update(nested_structure)
            else:
                field_info = self._analyze_value(value, field_name, type_name)
                logger.debug("analyze_structure: Created field_info=%s", field_info)
                fields.append(field_info)
        self._analyzed_structure[type_name] = fields
        logger.debug("analyze_structure: Final structure for %s: %s", type_name, self._analyzed_structure)

        # Add id field to tables that don't have an explicit primary key
        for type_name, fields in self._analyzed_structure.items():
            if type_name.endswith("_association"):
                continue  # Skip association tables
            has_explicit_pk = any(field.metadata.get("primary_key", False) for field in fields)
            if not has_explicit_pk:
                # Add id field to the analyzed structure
                id_field = FieldInfo(
                    name="id",
                    python_type=int,
                    nullable=False,
                    metadata={"primary_key": True},
                    description="Primary key",
                )
                fields.insert(0, id_field)  # Insert at the beginning of the fields list

        return self._analyzed_structure

    def create_association_table(
        self: Self,
        table_name: str,
        left_table: str,
        right_table: str,
        left_column: str,
        right_column: str,
        metadata: MetaData,
    ) -> Table:
        """Create an association table for many-to-many relationships.

        Args:
            table_name: Name of the association table.
            left_table: Name of the left table in the relationship.
            right_table: Name of the right table in the relationship.
            left_column: Name of the column referencing the left table.
            right_column: Name of the column referencing the right table.
            metadata: SQLAlchemy metadata object.

        Returns:
            Table: The created association table.
        """
        # For self-referential relationships, use different column names
        if left_table == right_table:
            right_column = f"related_{right_column}"

        return Table(
            table_name,
            metadata,
            Column(
                left_column,
                Integer,
                ForeignKey(f"{left_table}.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
            Column(
                right_column,
                Integer,
                ForeignKey(f"{right_table}.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
        )

    def generate_sqlalchemy_models(self: Self) -> List[Type[DeclarativeBase]]:
        """Generate SQLAlchemy models from the analyzed structure.

        This method generates SQLAlchemy model classes based on the analyzed structure.
        It handles:
        - Table definitions with appropriate columns
        - Primary keys (single and compound)
        - Foreign key relationships
        - Many-to-many relationships using association tables
        - Reference tables for enumerated values
        - Custom field types and constraints

        The generation is performed in two passes:
        1. First pass: Create all model classes with columns and primary keys
        2. Second pass: Add relationships and association tables

        Returns:
            A list of SQLAlchemy model classes.

        Example:
            ```python
            generator = SchemaGenerator(data)
            models = generator.generate_sqlalchemy_models()
            # Returns: [User, Address, Order, ...]
            ```
        """
        if not self._analyzed_structure:
            self.analyze_structure()

        # Base class for all models (using a shared MetaData)
        class Base(DeclarativeBase):
            pass

        generated_models: Dict[str, Type[DeclarativeBase]] = {}
        association_tables: Dict[str, Table] = {}

        # Helper to get SQLAlchemy type
        def get_sqla_type(field_info: FieldInfo) -> Type[Column]:
            if field_info.is_reference_table:
                return String
            py_type = field_info.python_type
            if py_type in self._type_mapping:
                return self._type_mapping[py_type]
            if py_type is None or py_type is type(None):
                return String  # fallback
            return String  # fallback

        # First pass: create all model classes with columns and primary keys
        for type_name, fields in self._analyzed_structure.items():
            attrs = {"__tablename__": type_name}
            has_explicit_pk = False

            # Add regular columns
            for field_iter in fields:
                if field_iter.is_many_to_many:
                    continue  # handled in second pass
                if field_iter.is_relationship and field_iter.is_list:
                    continue  # handled in second pass
                if field_iter.is_relationship and not field_iter.is_list:
                    # Add FK column for non-list relationships
                    fk_col = f"{field_iter.name}_id"
                    attrs[fk_col] = Column(
                        Integer,
                        ForeignKey(f"{field_iter.relationship_type}.id", ondelete="SET NULL"),
                        nullable=field_iter.nullable,
                    )
                    continue
                elif field_iter.is_reference_table:
                    attrs[field_iter.name] = Column(String, nullable=field_iter.nullable)
                else:
                    col_type = get_sqla_type(field_iter)
                    col_kwargs = {"nullable": field_iter.nullable}

                    # Handle primary key
                    if field_iter.metadata.get("primary_key", False):
                        col_kwargs["primary_key"] = True
                        has_explicit_pk = True
                    if field_iter.metadata.get("unique", False):
                        col_kwargs["unique"] = True
                    if "default" in field_iter.metadata:
                        col_kwargs["default"] = field_iter.metadata["default"]
                    if col_type is String and "max_len" in field_iter.metadata:
                        col_type = String(field_iter.metadata["max_len"])
                    attrs[field_iter.name] = Column(col_type, **col_kwargs)

            # Add an id column as primary key if no explicit primary key is defined
            # Skip for association tables as they'll be created in the second pass
            if not has_explicit_pk and not type_name.endswith("_association"):
                attrs["id"] = Column(Integer, primary_key=True, autoincrement=True)

            # Create the model
            model = type(type_name, (Base,), attrs)
            generated_models[type_name] = model

        # Second pass: create association tables and add relationships
        for type_name, fields in self._analyzed_structure.items():
            model = generated_models[type_name]

            for field_iter in fields:
                if not field_iter.is_relationship:
                    continue

                if field_iter.is_many_to_many:
                    # Create association table if not already created
                    assoc_table = self.create_association_table(
                        field_iter.association_table_name or f"{type_name}_{field_iter.relationship_type}_association",
                        type_name,
                        field_iter.relationship_type,
                        f"{type_name}_id",
                        f"{field_iter.relationship_type}_id",
                        Base.metadata,
                    )

                    # Get the table name robustly
                    table_name = None
                    for attr in ["name", "tablename", "__tablename__", "key", "__table__"]:
                        if hasattr(assoc_table, attr):
                            table_name = getattr(assoc_table, attr)
                            logger.debug("Found table name using attribute '%s': %s", attr, table_name)
                            break
                    if table_name is None:
                        table_name = str(assoc_table)
                        logger.debug("Fallback table name: %s", table_name)

                    if table_name not in association_tables:
                        logger.debug("Registering association table: %s", table_name)
                        association_tables[table_name] = assoc_table

                    # Add relationship to both sides
                    setattr(
                        model,
                        field_iter.name,
                        relationship(
                            field_iter.relationship_type.capitalize(),
                            secondary=assoc_table,
                            back_populates=None,  # No back-population to avoid circular references
                            lazy="joined",
                        ),
                    )

                    # Add reverse relationship if not self-referential
                    if type_name != field_iter.relationship_type:
                        related_model = generated_models[field_iter.relationship_type]
                        reverse_name = self._singularize(type_name) + "s"
                        setattr(
                            related_model,
                            reverse_name,
                            relationship(
                                type_name.capitalize(), secondary=assoc_table, back_populates=None, lazy="joined"
                            ),
                        )
                elif field_iter.is_list:
                    # One-to-many relationship
                    setattr(
                        model,
                        field_iter.name,
                        relationship(field_iter.relationship_type.capitalize(), back_populates=None, lazy="joined"),
                    )
                else:
                    # Many-to-one relationship
                    setattr(
                        model,
                        field_iter.name,
                        relationship(field_iter.relationship_type.capitalize(), back_populates=None, lazy="joined"),
                    )

        # Add reference table models with proper primary keys and unique constraint
        for _type_name, fields in self._analyzed_structure.items():
            for field_iter in fields:
                if field_iter.is_reference_table:
                    ref_table_name = field_iter.reference_table_name
                    if ref_table_name and ref_table_name not in generated_models:
                        # Create the Table for the reference table
                        columns = [
                            Column("id", Integer, primary_key=True, autoincrement=True),
                            Column("value", String, nullable=False),
                        ]
                        if field_iter.description:
                            columns.append(Column("description", String, nullable=True))
                        ref_table = Table(
                            ref_table_name,
                            Base.metadata,
                            *columns,
                            UniqueConstraint("value", name=f"uq_{ref_table_name}_value"),
                        )
                        generated_models[ref_table_name] = ref_table

        # Ensure all association tables are registered in Base.metadata.tables
        for assoc_table in association_tables.values():
            logger.debug("Registering association table in metadata: %s", dir(assoc_table))
            logger.debug("Association table type: %s, repr: %s", type(assoc_table), repr(assoc_table))
            table_name = None
            for attr in ["name", "tablename", "__tablename__", "key", "__table__"]:
                if hasattr(assoc_table, attr):
                    table_name = getattr(assoc_table, attr)
                    logger.debug("Found table name for registration using attribute '%s': %s", attr, table_name)
                    break
            if table_name is None:
                table_name = str(assoc_table)
                logger.debug("Fallback table name for registration: %s", table_name)
            if table_name not in Base.metadata.tables:
                logger.debug("Adding table to Base.metadata: %s", table_name)
                Base.metadata._add_table(table_name, None, assoc_table)

        return list(generated_models.values()) + list(association_tables.values())

    def generate_pydantic_models(self: Self) -> List[Type[BaseModel]]:
        """Generate Pydantic models from the analyzed structure.

        This method generates Pydantic model classes based on the analyzed structure.
        It handles:
        - Field definitions with appropriate types
        - Validation rules from metadata
        - Nested models for relationships
        - Optional fields and default values
        - Custom validators and constraints

        The generation process:
        1. Creates base field definitions
        2. Adds validation rules from metadata
        3. Handles relationships and nested models
        4. Updates field types with actual model references

        Returns:
            A list of Pydantic model classes.

        Example:
            ```python
            generator = SchemaGenerator(data)
            models = generator.generate_pydantic_models()
            # Returns: [UserModel, AddressModel, OrderModel, ...]
            ```
        """
        if not self._analyzed_structure:
            self.analyze_structure()

        # Track generated models to avoid duplicates
        generated_models: Dict[str, Type[BaseModel]] = {}

        def create_field_definition(field_info: FieldInfo) -> tuple:
            """Create a Pydantic field definition from FieldInfo."""
            # Get the base type
            if field_info.is_relationship:
                if field_info.is_list:
                    base_type = List[Any]  # Temporary, will be updated
                else:
                    base_type = Any  # Temporary, will be updated
            else:
                base_type = field_info.python_type

            field_kwargs = {}
            metadata = field_info.metadata
            # Handle choices (Literal) first so it can wrap Optional if needed
            if "choices" in metadata:
                choices = metadata["choices"]
                if isinstance(choices, list) and choices:
                    base_type = Literal[tuple(choices)]  # type: ignore
            # Handle nullable fields
            if field_info.nullable:
                base_type = Optional[base_type]
                field_kwargs["default"] = None
            # Add metadata-based validations
            if "max_len" in metadata:
                field_kwargs["max_length"] = metadata["max_len"]
            if "min_len" in metadata:
                field_kwargs["min_length"] = metadata["min_len"]
            if "regex" in metadata:
                field_kwargs["pattern"] = metadata["regex"]
            if "min_value" in metadata:
                field_kwargs["ge"] = metadata["min_value"]
            if "max_value" in metadata:
                field_kwargs["le"] = metadata["max_value"]
            if "default" in metadata:
                field_kwargs["default"] = metadata["default"]
            if field_info.description:
                field_kwargs["description"] = field_info.description
            return (base_type, PydanticField(**field_kwargs))

        def create_model_for_type(type_name: str) -> Type[BaseModel]:
            """Create a Pydantic model for a given type."""
            # If we've already generated this model, return it
            if type_name in generated_models:
                return generated_models[type_name]

            # Get the fields for this type
            fields = self._analyzed_structure[type_name]

            # Create field definitions
            field_definitions = {}
            for field_info in fields:
                field_name = field_info.name
                field_type, field_kwargs = create_field_definition(field_info)
                field_definitions[field_name] = (field_type, field_kwargs)

            # Create the model
            model = create_model(type_name, **field_definitions, __base__=BaseModel)

            # Store the generated model
            generated_models[type_name] = model

            # Update relationship fields with actual model types
            for field_info in fields:
                if field_info.is_relationship:
                    field_name = field_info.name
                    related_model = generated_models.get(field_info.relationship_type)
                    if related_model:
                        if field_info.is_list:
                            field_type = List[Optional[related_model]]
                        else:
                            field_type = Optional[related_model]
                        # Update the field type
                        model.__annotations__[field_name] = field_type
                        # Update the field in the model
                        field = model.model_fields[field_name]
                        field.annotation = field_type

            return model

        # Generate models for all types
        for type_name in self._analyzed_structure:
            create_model_for_type(type_name)

        return list(generated_models.values())

    def visualize_schema(self: Self) -> None:
        """Display a visualization of the generated schema using Rich.

        This method creates a rich console visualization of the analyzed schema structure.
        It shows:
        - Field names and types
        - Nullability
        - Relationships
        - Foreign keys
        - Reference tables
        - Many-to-many relationships
        - Field metadata

        The visualization is formatted as a table with color-coded columns for
        better readability.

        Example:
            ```python
            generator = SchemaGenerator(data)
            generator.visualize_schema()
            # Displays a rich table in the console showing the schema structure
            ```
        """
        if not self._analyzed_structure:
            self.analyze_structure()

        for type_name, fields in self._analyzed_structure.items():
            table = RichTable(title=f"Schema Structure: {type_name}")
            table.add_column("Field", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Nullable", style="green")
            table.add_column("Primary Key", style="yellow")
            table.add_column("Relationship", style="yellow")
            table.add_column("Is List", style="blue")
            table.add_column("Is FK", style="red")
            table.add_column("FK To", style="red")
            table.add_column("Is Ref Table", style="blue")
            table.add_column("Ref Table Name", style="blue")
            table.add_column("Is M2M", style="blue")
            table.add_column("Assoc Table", style="blue")
            table.add_column("Metadata", style="blue")

            for field_iter in fields:
                metadata_str = ", ".join(f"{k}={v}" for k, v in field_iter.metadata.items())
                is_primary_key = field_iter.metadata.get("primary_key", False) or field_iter.name == "id"
                table.add_row(
                    field_iter.name,
                    field_iter.python_type.__name__,
                    str(field_iter.nullable),
                    str(is_primary_key),
                    field_iter.relationship_type if field_iter.is_relationship else "",
                    str(field_iter.is_list),
                    str(field_iter.is_foreign_key),
                    field_iter.foreign_key_to or "",
                    str(field_iter.is_reference_table),
                    field_iter.reference_table_name or "",
                    str(field_iter.is_many_to_many),
                    field_iter.association_table_name or "",
                    metadata_str,
                )

            self.console.print(table)
            self.console.print()  # Add a blank line between tables
