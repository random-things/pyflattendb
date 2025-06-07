"""Demo script showcasing PyFlattenDB features with a realistic e-commerce example.

This script demonstrates:
- Complex nested data structures
- Different relationship types (one-to-one, one-to-many, many-to-many)
- Reference tables for enumerated values
- Custom field metadata and validations
- Schema visualization
- Logging configuration for debugging
"""

import argparse
import logging

from rich.console import Console
from rich.panel import Panel

from pyflattendb import SchemaGenerator


def configure_logging(debug: bool = False) -> None:
    """Configure logging for the application.

    Args:
        debug: If True, enables debug logging for pyflattendb.
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handler
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Add the handler to the root logger
    root_logger.addHandler(console_handler)

    # Configure pyflattendb logger
    pyflattendb_logger = logging.getLogger("pyflattendb")
    if debug:
        pyflattendb_logger.setLevel(logging.DEBUG)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logging.info("Debug logging enabled for pyflattendb")


def main() -> None:
    """Run the demo."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PyFlattenDB Demo")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging
    configure_logging(args.debug)

    # Create a console instance for better output formatting
    console = Console()

    # Create a sample e-commerce data structure
    data = {
        "store": {
            "name": "TechGadgets",
            "website": "https://techgadgets.example.com",
            "status": "active",
            "address": {
                "street": "123 Tech Street",
                "city": "Silicon Valley",
                "state": "CA",
                "zip": "94025",
                "country": "USA",
            },
            "departments": [
                {
                    "name": "Electronics",
                    "manager": {
                        "name": "Alice Smith",
                        "email": "alice@techgadgets.example.com",
                        "role": "department_manager",
                    },
                },
                {
                    "name": "Accessories",
                    "manager": {
                        "name": "Bob Johnson",
                        "email": "bob@techgadgets.example.com",
                        "role": "department_manager",
                    },
                },
            ],
            "products": [
                {
                    "name": "SmartPhone X",
                    "sku": "SPX-001",
                    "price": 999.99,
                    "status": "in_stock",
                    "categories": [{"name": "Electronics"}, {"name": "Phones"}],
                    "specifications": {"color": "black", "storage": "256GB", "warranty": "2 years"},
                },
                {
                    "name": "Wireless Earbuds",
                    "sku": "WEB-001",
                    "price": 199.99,
                    "status": "low_stock",
                    "categories": [{"name": "Electronics"}, {"name": "Accessories"}],
                    "specifications": {"color": "white", "battery_life": "8 hours", "warranty": "1 year"},
                },
            ],
            "orders": [
                {
                    "order_number": "ORD-001",
                    "status": "processing",
                    "customer": {"name": "John Doe", "email": "john@example.com", "phone": "+1-555-0123"},
                    "items": [
                        {"product": "SmartPhone X", "quantity": 1, "price": 999.99},
                        {"product": "Wireless Earbuds", "quantity": 2, "price": 199.99},
                    ],
                    "shipping_address": {
                        "street": "456 Customer Ave",
                        "city": "San Francisco",
                        "state": "CA",
                        "zip": "94105",
                        "country": "USA",
                    },
                    "payment": {"method": "credit_card", "status": "paid", "amount": 1399.97},
                }
            ],
            # Metadata for fine-grained control
            "_pyflattendb": {
                "store.status": {
                    "is_reference_table": True,
                    "choices": ["active", "inactive", "maintenance"],
                    "description": "Current store status",
                },
                "store.address": {"description": "Store's physical address"},
                "product.status": {
                    "is_reference_table": True,
                    "choices": ["in_stock", "low_stock", "out_of_stock", "discontinued"],
                    "description": "Current product availability status",
                },
                "product.categories": {"is_many_to_many": True, "description": "Product categories"},
                "order.status": {
                    "is_reference_table": True,
                    "choices": ["pending", "processing", "shipped", "delivered", "cancelled"],
                    "description": "Current order status",
                },
                "order.payment.method": {
                    "is_reference_table": True,
                    "choices": ["credit_card", "paypal", "bank_transfer"],
                    "description": "Payment method used",
                },
                "order.payment.status": {
                    "is_reference_table": True,
                    "choices": ["pending", "paid", "failed", "refunded"],
                    "description": "Payment status",
                },
            },
        }
    }

    # Create a panel with a description
    console.print(
        Panel.fit(
            "This demo showcases PyFlattenDB's ability to handle complex data structures:\n"
            "• Nested objects (store → address, departments → manager)\n"
            "• One-to-many relationships (store → products, store → orders)\n"
            "• Many-to-many relationships (products ↔ categories)\n"
            "• Reference tables (status fields, payment methods)\n"
            "• Custom metadata and validations\n"
            "• Debug logging (use --debug flag to enable)",
            title="PyFlattenDB Demo",
            border_style="blue",
        )
    )

    # Initialize the schema generator
    console.print("\n[bold blue]Initializing SchemaGenerator...[/bold blue]")
    generator = SchemaGenerator(data)

    # Generate and display the schema
    console.print("\n[bold blue]Analyzing data structure...[/bold blue]")
    generator.analyze_structure()

    console.print("\n[bold blue]Generating SQLAlchemy models...[/bold blue]")
    sqlalchemy_models = generator.generate_sqlalchemy_models()
    console.print(f"[green]Generated {len(sqlalchemy_models)} SQLAlchemy models[/green]")

    console.print("\n[bold blue]Generating Pydantic models...[/bold blue]")
    pydantic_models = generator.generate_pydantic_models()
    console.print(f"[green]Generated {len(pydantic_models)} Pydantic models[/green]")

    # Visualize the schema
    console.print("\n[bold blue]Schema Visualization:[/bold blue]")
    generator.visualize_schema()

    # Print some example usage
    console.print("\n[bold blue]Example Usage:[/bold blue]")
    console.print(
        """
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
    """
    )


if __name__ == "__main__":
    main()
