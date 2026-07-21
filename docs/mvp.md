# Minimum Viable Product

## Mandatory MVP

- Backoffice authentication;
- secure PBKDF2 password storage;
- administrator and common-user authorization;
- assignment of every common user to one branch;
- stock addition, removal, and consultation;
- prevention of negative stock;
- user management by the administrator;
- soft deletion of users;
- product listing from the official External Product API;
- product details by numeric ID or SKU;
- simple product selection or search;
- product-existence validation before a stock operation;
- controlled errors when the Product API is unavailable, slow, or returns an invalid response;
- MCP product tools;
- stock consultation through MCP;
- one AI agent;
- product questions;
- stock questions;
- branch questions;
- simple shopping-list checks;
- a public web interface served by FastAPI;
- clear errors for unavailable or insufficient information;
- critical automated and integration tests;
- project documentation and final presentation.

## Optional Product API features

- category listing and filtering;
- supplier listing and filtering;
- advanced price, discontinued-status, and sorting filters;
- dedicated search beyond the simple MVP selection flow.

## Explicitly excluded from the MVP

- WebSockets;
- streamed responses;
- conversation history;
- creation of multiple administrators;
- an advanced dashboard;
- charts;
- notifications;
- complex visual design;
- a mobile application;
- direct SQL access for the agent or MCP;
- stock features in the administrator interface;
- stock changes through MCP.
