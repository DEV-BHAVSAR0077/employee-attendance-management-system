#!/bin/bash

# Employee Attendance Analysis System - Quick Start Script

echo "=================================="
echo "Employee Attendance System Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8 or higher from https://www.python.org/"
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"
echo ""

# Install dependencies
echo "Installing required packages..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo "✓ All packages installed successfully"
echo ""

# Create necessary directories
echo "Setting up directories..."
mkdir -p uploads
echo "✓ Directories created"
echo ""

echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "To start the application, run:"
echo "  python3 app.py"
echo ""
echo "Then open your browser and go to:"
echo "  http://localhost:5000"
echo ""
echo "Sample attendance file included:"
echo "  sample_attendance.xlsx"
echo ""
echo "=================================="
