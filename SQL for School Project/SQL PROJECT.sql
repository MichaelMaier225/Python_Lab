use orange_database;


CREATE TABLE Equipment (
    Equipment_ID INT PRIMARY KEY,
    Equipment_Name VARCHAR(255)
);

CREATE TABLE Vehicle (
    Vehicle_ID INT PRIMARY KEY,
    Make VARCHAR(255),
    Model VARCHAR(255),
    Year INT,
    License_Plate VARCHAR(255),
    Customer_ID INT
);
