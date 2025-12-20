## ADDED Requirements
### Requirement: Mock Smart Shelf Stock Alerts
The system SHALL publish shelf inventory payloads over MQTT every two seconds and surface a restock alert when remaining stock is at or below 30 percent of capacity.

#### Scenario: Normal stock state
- **GIVEN** the mock publisher emits a payload with current_stock greater than 3 and capacity of 10
- **WHEN** the cloud dashboard receives the message
- **THEN** it displays a green status indicator and does not raise a restock alert

#### Scenario: Low stock alert
- **GIVEN** the mock publisher emits a payload with current_stock less than or equal to 3 and capacity of 10
- **WHEN** the cloud dashboard receives the message
- **THEN** it displays a red restock alert message and highlights the low inventory state
