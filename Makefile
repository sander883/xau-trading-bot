.PHONY: help install install-dev clean test lint format backtest run logs

help:
	@echo "AI Trading Bot for XAUUSD - Available Commands"
	@echo "=============================================="
	@echo "make install        - Install production dependencies"
	@echo "make install-dev    - Install development dependencies"
	@echo "make run            - Run trading bot in live mode"
	@echo "make backtest       - Run backtesting"
	@echo "make logs           - Show live logs"
	@echo "make test           - Run tests"
	@echo "make lint           - Run code linting"
	@echo "make format         - Format code with black"
	@echo "make clean          - Clean cache and temp files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	python main.py

backtest:
	python main.py backtest

logs:
	tail -f logs/trading_bot.log

test:
	pytest tests/ -v --cov=src

lint:
	flake8 src/ config/ main.py
	pylint src/ config/ main.py

format:
	black src/ config/ main.py

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

.DEFAULT_GOAL := help
