#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Detect docker compose command (V2 uses 'docker compose', V1 uses 'docker-compose')
get_compose_cmd() {
    if docker compose version &>/dev/null; then
        echo "docker compose"
    elif docker-compose --version &>/dev/null; then
        echo "docker-compose"
    else
        echo ""
    fi
}

COMPOSE_CMD=$(get_compose_cmd)

# Function to print colored header
print_header() {
    echo -e "${CYAN}=====================================${NC}"
    echo -e "${CYAN}   Media Search API - Setup Menu${NC}"
    echo -e "${CYAN}=====================================${NC}"
}

# Function to print menu options
print_menu() {
    echo -e "${BLUE}1)${NC} Start Docker containers"
    echo -e "${BLUE}2)${NC} Stop Docker containers"
    echo -e "${BLUE}3)${NC} View container logs"
    echo -e "${BLUE}0)${NC} Exit"
    echo -e "${CYAN}=====================================${NC}"
}

# Function to check required environment variables
check_env_vars() {
    local missing_vars=()

    if [[ -z "${PEXELS_API_KEY}" ]]; then
        missing_vars+=("PEXELS_API_KEY")
    fi

    if [[ -z "${PIXABAY_API_KEY}" ]]; then
        missing_vars+=("PIXABAY_API_KEY")
    fi

    if [[ -z "${OPENAI_API_KEY}" ]]; then
        missing_vars+=("OPENAI_API_KEY")
    fi

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${RED}Error: Missing required environment variables:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "${YELLOW}  - ${var}${NC}"
        done
        echo -e "${YELLOW}Please set these variables before starting containers.${NC}"
        return 1
    fi

    return 0
}

# Function to start Docker containers
start_containers() {
    if [[ -z "$COMPOSE_CMD" ]]; then
        echo -e "${RED}Error: Docker Compose not found. Please install Docker Compose.${NC}"
        return 1
    fi

    echo -e "${YELLOW}Checking environment variables...${NC}"

    if ! check_env_vars; then
        return 1
    fi

    echo -e "${YELLOW}Removing any existing containers...${NC}"
    $COMPOSE_CMD down --remove-orphans 2>/dev/null
    docker rm -f media-search-api media-search-redis media-search-redis-commander 2>/dev/null

    echo -e "${GREEN}Starting Docker containers...${NC}"
    $COMPOSE_CMD up -d --build

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}Containers started successfully!${NC}"
    else
        echo -e "${RED}Failed to start containers.${NC}"
        return 1
    fi
}

# Function to stop Docker containers
stop_containers() {
    if [[ -z "$COMPOSE_CMD" ]]; then
        echo -e "${RED}Error: Docker Compose not found. Please install Docker Compose.${NC}"
        return 1
    fi

    echo -e "${YELLOW}Stopping Docker containers...${NC}"
    $COMPOSE_CMD down

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}Containers stopped successfully!${NC}"
    else
        echo -e "${RED}Failed to stop containers.${NC}"
        return 1
    fi
}

# Function to view container logs
view_logs() {
    if [[ -z "$COMPOSE_CMD" ]]; then
        echo -e "${RED}Error: Docker Compose not found. Please install Docker Compose.${NC}"
        return 1
    fi

    echo -e "${YELLOW}Viewing container logs (Ctrl+C to exit)...${NC}"
    $COMPOSE_CMD logs -f
}

# Main menu loop
main() {
    while true; do
        echo ""
        print_header
        print_menu

        read -p "Select an option [0-3]: " choice
        echo ""

        case $choice in
            1)
                start_containers
                ;;
            2)
                stop_containers
                ;;
            3)
                view_logs
                ;;
            0)
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option. Please select 1-4.${NC}"
                ;;
        esac
    done
}

# Run main function
main
