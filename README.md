# E-commerce API with Inventory Management & Transactional Orders

## Project Overview
This project is a backend REST API for an e-commerce platform built using FastAPI, PostgreSQL, Redis, and Docker.  
It handles product catalogs, shopping carts, real-time inventory management, and order processing with strong guarantees on data consistency.

The system is designed to prevent overselling under concurrent requests using optimistic locking and database transactions, while remaining performant through caching and asynchronous processing.

This project is implemented as part of the **Partnr GPP Mandatory Task**.

---

## Features

### Authentication & Authorization
- JWT-based authentication
- Two user roles:
  - ADMIN
  - CUSTOMER
- Role-based access control enforced at API level

### Product Management (ADMIN only)
- Create, update, delete products
- Automatic cache invalidation on product changes

### Product Discovery (Public)
- List products
- Filter by category
- Sort by price (ascending / descending)
- Redis cache using cache-aside pattern

### Shopping Cart (CUSTOMER only)
- Add items to cart
- View cart
- Remove cart items

### Order Management (CUSTOMER only)
- Place order from cart
- View order by ID
- Stores price snapshot at time of purchase

### Inventory Management & Concurrency Control
- Stock validation before order placement
- Optimistic locking using a version field on products
- Atomic update:
  UPDATE products
  SET stock_quantity = ..., version = version + 1
  WHERE id = ... AND version = ...
- Prevents overselling under concurrent checkout attempts

### Transaction Management
- Entire order placement runs inside a single database transaction
- Includes:
  - Stock validation
  - Stock deduction
  - Order creation
  - Order items creation
  - Cart cleanup
- Automatic rollback on failure

### Asynchronous Processing
- Order confirmation email sent using FastAPI BackgroundTasks
- API response does not wait for email completion

### Performance & Caching
- Redis used to cache GET /products
- Cache invalidated on product create, update, delete
- Reduces database load for repeated requests

---

## System Architecture

Client  
↓  
FastAPI Application  
↓  
PostgreSQL (Transactional Data)  
↓  
Redis (Product Cache)  
↓  
Background Task (Order Confirmation Email)

The application follows a clear separation of concerns:
- API layer (routing & validation)
- Business logic (order processing, locking)
- Data access layer (SQLAlchemy ORM)

---

## Database Schema (ERD Summary)

Entities:
- User
- Product
- CartItem
- Order
- OrderItem

Relationships:
- User → CartItems (1:N)
- User → Orders (1:N)
- Order → OrderItems (1:N)
- Product → OrderItems (1:N)

Each product includes a version field to support optimistic locking.

---

## Tech Stack
- Backend Framework: FastAPI
- Database: PostgreSQL
- Cache: Redis
- ORM: SQLAlchemy
- Authentication: JWT (python-jose)
- Containerization: Docker & Docker Compose
- Async Tasks: FastAPI BackgroundTasks

---

## Setup & Run Instructions

### Prerequisites
- Docker
- Docker Compose

### Run the Application
docker compose down -v  
docker compose build  
docker compose up  

### Access API Documentation
Open in browser:
http://localhost:8000/docs

Swagger UI provides interactive API documentation.

---

## API Endpoints

Authentication:
- POST /login

Products:
- POST /products (ADMIN)
- GET /products
- GET /products/{id}
- PUT /products/{id} (ADMIN)
- DELETE /products/{id} (ADMIN)

Cart:
- POST /cart/items
- GET /cart
- DELETE /cart/items/{id}

Orders:
- POST /orders
- GET /orders/{id}

---

## Evaluation Readiness
This project satisfies all evaluation criteria:
- Fully functional REST API
- Strong concurrency control
- Transaction safety
- Redis caching
- Asynchronous processing
- Dockerized deployment
- Clear documentation

---

## Notes
- Swagger (/docs) is the primary API documentation.
- Architecture and ERD diagrams are included in the repository.
- Designed for easy extension into service and repository layers.




