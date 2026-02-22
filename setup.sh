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
    echo -e "${BLUE}4)${NC} Backup database"
    echo -e "${BLUE}5)${NC} Show service URL"
    echo -e "${BLUE}6)${NC} Run tests"
    echo -e "${BLUE}7)${NC} Install dependencies (requirements.txt)"
    echo -e "${BLUE}8)${NC} Show usage (generate_media.py)"
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

# Function to backup the database
backup_database() {
    local container_name="media-search-api"
    local db_path="/app/data/prompts.db"
    local backup_dir="./backups"
    local timestamp=$(date +"%Y_%m_%d_%H_%M_%S")
    local backup_file="${backup_dir}/media_${timestamp}.db"

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo -e "${RED}Error: Container '${container_name}' is not running.${NC}"
        echo -e "${YELLOW}Start the containers first with option 1.${NC}"
        return 1
    fi

    # Create backup directory if it doesn't exist
    mkdir -p "$backup_dir"

    echo -e "${YELLOW}Backing up database...${NC}"

    # Copy database from container
    if docker cp "${container_name}:${db_path}" "$backup_file" 2>/dev/null; then
        echo -e "${GREEN}Database backed up successfully!${NC}"
        echo -e "${CYAN}Backup location: ${backup_file}${NC}"
    else
        echo -e "${RED}Failed to backup database.${NC}"
        echo -e "${YELLOW}The database file may not exist yet (no data stored).${NC}"
        return 1
    fi
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"

    # Resolve the directory containing this script so the command works
    # regardless of where setup.sh is invoked from.
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Prefer the project virtual environment if it exists; otherwise fall
    # back to whatever pytest is on PATH.
    local pytest_cmd
    if [[ -f "${script_dir}/.venv/bin/pytest" ]]; then
        pytest_cmd="${script_dir}/.venv/bin/pytest"
    elif [[ -f "${HOME}/.virtualenvs/media/bin/pytest" ]]; then
        pytest_cmd="${HOME}/.virtualenvs/media/bin/pytest"
    elif command -v pytest &>/dev/null; then
        pytest_cmd="pytest"
    else
        echo -e "${RED}Error: pytest not found. Install dependencies first (pip install -e '.[dev]').${NC}"
        return 1
    fi

    echo -e "${CYAN}$ (cd \"${script_dir}\" && \"${pytest_cmd}\" -q)${NC}"
    (cd "$script_dir" && "$pytest_cmd" -q)

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
    else
        echo -e "${RED}Some tests failed.${NC}"
        return 1
    fi

    # --- Real workflow test: generate_media.py against e2e golden ---
    echo ""
    echo -e "${YELLOW}Running real workflow: generate_media.py...${NC}"

    local input="${script_dir}/third_party/contracts/goldens/e2e/example_episode/AssetManifest.json"
    local timestamp
    timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"
    local output="/tmp/AssetManifest.media_${timestamp}.json"

    local python_cmd
    if [[ -f "${script_dir}/.venv/bin/python" ]]; then
        python_cmd="${script_dir}/.venv/bin/python"
    elif [[ -f "${HOME}/.virtualenvs/media/bin/python" ]]; then
        python_cmd="${HOME}/.virtualenvs/media/bin/python"
    elif command -v python3 &>/dev/null; then
        python_cmd="python3"
    else
        python_cmd="python"
    fi

    echo -e "${CYAN}$ \"${python_cmd}\" scripts/generate_media.py \\${NC}"
    echo -e "${CYAN}      --input  \"${input}\" \\${NC}"
    echo -e "${CYAN}      --output \"${output}\"${NC}"
    (cd "$script_dir" && "$python_cmd" scripts/generate_media.py \
        --input  "$input" \
        --output "$output")

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}Workflow test failed.${NC}"
        return 1
    fi

    echo -e "${CYAN}$ ls -l \"${output}\"${NC}"
    ls -l "$output"

    local size
    size=$(stat -c%s "$output" 2>/dev/null || stat -f%z "$output" 2>/dev/null)
    if [[ -z "$size" || "$size" -eq 0 ]]; then
        echo -e "${RED}Error: output file is empty.${NC}"
        rm -f "$output"
        return 1
    fi

    echo -e "${GREEN}Workflow test passed! (${size} bytes)${NC}"
    echo -e "${CYAN}$ rm \"${output}\"${NC}"
    rm -f "$output"
    echo -e "${GREEN}Output cleaned up.${NC}"
}

# Function to install Python dependencies from requirements.txt
install_requirements() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    local pip_cmd
    if [[ -f "${script_dir}/.venv/bin/pip" ]]; then
        pip_cmd="${script_dir}/.venv/bin/pip"
    elif [[ -f "${HOME}/.virtualenvs/media/bin/pip" ]]; then
        pip_cmd="${HOME}/.virtualenvs/media/bin/pip"
    elif command -v pip3 &>/dev/null; then
        pip_cmd="pip3"
    elif command -v pip &>/dev/null; then
        pip_cmd="pip"
    else
        echo -e "${RED}Error: pip not found. Please install Python/pip first.${NC}"
        return 1
    fi

    if [[ ! -f "${script_dir}/requirements.txt" ]]; then
        echo -e "${RED}Error: requirements.txt not found in ${script_dir}.${NC}"
        return 1
    fi

    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    "$pip_cmd" install -r "${script_dir}/requirements.txt"

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}Dependencies installed successfully!${NC}"
    else
        echo -e "${RED}Failed to install dependencies.${NC}"
        return 1
    fi
}

# Function to show generate_media.py usage
show_generate_usage() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    echo -e "${GREEN}generate_media.py — resolve an AssetManifest into AssetManifest.media.json${NC}"
    echo ""
    echo -e "${CYAN}Basic usage:${NC}"
    echo -e "  python ${script_dir}/scripts/generate_media.py \\"
    echo -e "      --input  /path/to/AssetManifest.json \\"
    echo -e "      --output /path/to/AssetManifest.media.json"
    echo ""
    echo -e "${CYAN}Fail if any asset is missing (no placeholders allowed):${NC}"
    echo -e "  python ${script_dir}/scripts/generate_media.py \\"
    echo -e "      --input  /path/to/AssetManifest.json \\"
    echo -e "      --output /path/to/AssetManifest.media.json \\"
    echo -e "      --strict"
    echo ""
    echo -e "${CYAN}Short flags:${NC}"
    echo -e "  python ${script_dir}/scripts/generate_media.py \\"
    echo -e "      -i /path/to/AssetManifest.json \\"
    echo -e "      -o /path/to/AssetManifest.media.json"
    echo ""
    echo -e "${CYAN}Via make:${NC}"
    echo -e "  make generate-media \\"
    echo -e "      INPUT=/path/to/AssetManifest.json \\"
    echo -e "      OUTPUT=/path/to/AssetManifest.media.json"
    echo ""
    echo -e "${CYAN}Environment variables (optional):${NC}"
    echo -e "  MEDIA_LIBRARY_ROOT   — path to local asset library"
    echo -e "  LOCAL_ASSETS_ROOT    — path to local assets directory"
    echo ""
    echo -e "${CYAN}Exit codes:${NC}"
    echo -e "  0  resolved successfully"
    echo -e "  1  resolver error or invalid input"
    echo -e "  2  bad arguments / input file not found"
}

# Function to show service URL
show_service_url() {
    local private_ip=$(hostname -I | awk '{print $1}')

    if [[ -z "$private_ip" ]]; then
        echo -e "${RED}Error: Could not determine private IP address.${NC}"
        return 1
    fi

    echo -e "${GREEN}Service URLs:${NC}"
    echo -e "${CYAN}  API:      http://${private_ip}:28000${NC}"
    echo -e "${CYAN}  Docs:     http://${private_ip}:28000/docs${NC}"
    echo -e "${CYAN}  Health:   http://${private_ip}:28000/health${NC}"
}

# Main menu loop
main() {
    while true; do
        echo ""
        print_header
        print_menu

        read -p "Select an option [0-8]: " choice
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
            4)
                backup_database
                ;;
            5)
                show_service_url
                ;;
            6)
                run_tests
                ;;
            7)
                install_requirements
                ;;
            8)
                show_generate_usage
                ;;
            0)
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option. Please select 0-8.${NC}"
                ;;
        esac
    done
}

# Run main function
main
