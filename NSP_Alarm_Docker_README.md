# 📡 NSP Alarm Processing & Monitoring System (Dockerized)

![Docker](https://img.shields.io/badge/Docker-Enabled-blue)
![Python](https://img.shields.io/badge/Python-3.x-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Kafka](https://img.shields.io/badge/Kafka-Streaming-black)
![License](https://img.shields.io/badge/License-MIT-yellow)

A production-ready, containerized alarm processing system designed for
telecom NOC environments.\
This project integrates Huawei NSP alarm streams via Kafka, processes
them using Python, and stores them in PostgreSQL with real-time
monitoring capabilities.

------------------------------------------------------------------------

## 🚀 Overview

This system provides an end-to-end pipeline for handling network alarms:

**NSP → Kafka → Python Processing → PostgreSQL → CLI Monitoring /
Automation**

It enables real-time alarm ingestion, normalization, filtering, and
supports automation workflows such as alerting and ticket generation.

------------------------------------------------------------------------

## ✨ Key Features

-   Real-time NSP alarm ingestion via Kafka
-   High-performance Python-based processing engine
-   PostgreSQL storage with alarm lifecycle management
-   CLI-based alarm monitoring tool
-   Fully Dockerized deployment
-   Automation-ready (TT generation, alerts)

------------------------------------------------------------------------

## 🏗️ Architecture

NSP → Kafka → Python Consumer → PostgreSQL → CLI / Automation

------------------------------------------------------------------------

## 📁 Project Structure

kafka-python/ - alarm_cli.py - full_flow_main.py - kafka_consumer.py -
alarm_normalizer.py - alarm_filters.py - alarm_lifecycle.py -
alarm_cache.py - db.py - configuration.py - Dockerfile -
docker-compose.yml - requirements.txt - .env

------------------------------------------------------------------------

## ⚙️ Requirements

-   Docker & Docker Compose
-   Linux server
-   NSP access

------------------------------------------------------------------------

## 🚀 Quick Start

### Clone

git clone https://github.com/mizan23/kafka-python.git\
cd kafka-python

### Configure

Edit .env with DB credentials

### Run

docker-compose up -d --build

------------------------------------------------------------------------

## 🧪 CLI Usage

docker exec -it nsp-alarm-consumer python alarm_cli.py --watch 5

------------------------------------------------------------------------

## 🔄 Use Cases

-   Telecom NOC monitoring
-   Huawei alarm processing
-   Auto TT generation
-   Event-driven automation

------------------------------------------------------------------------

## 👨‍💻 Author

Mizanur Rahman\
mizanur.eee23@gmail.com\
https://github.com/mizan23

------------------------------------------------------------------------

## 📄 License

MIT License
