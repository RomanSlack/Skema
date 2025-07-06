#!/bin/bash

# Skema Database Backup Script
# This script creates automated backups of the PostgreSQL database

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="${POSTGRES_DB:-skema}"
DB_USER="${POSTGRES_USER:-skema_user}"
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[BACKUP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create backup directory
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        print_status "Created backup directory: $BACKUP_DIR"
    fi
}

# Function to wait for database
wait_for_database() {
    print_status "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            print_success "Database is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    print_error "Database not ready after $max_attempts attempts"
    return 1
}

# Function to create full database backup
create_full_backup() {
    local backup_file="$BACKUP_DIR/skema_full_backup_$TIMESTAMP.sql"
    
    print_status "Creating full database backup..."
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --clean --no-owner --no-privileges \
        --format=custom --compress=9 > "$backup_file.custom"; then
        
        # Also create a plain SQL backup for easy inspection
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            --verbose --clean --no-owner --no-privileges \
            --format=plain > "$backup_file"
        
        # Compress the plain SQL backup
        gzip "$backup_file"
        
        print_success "Full backup created: $backup_file.gz"
        print_success "Custom format backup: $backup_file.custom"
        
        # Get backup size
        local size=$(du -h "$backup_file.gz" | cut -f1)
        local custom_size=$(du -h "$backup_file.custom" | cut -f1)
        print_status "Backup sizes - SQL: $size, Custom: $custom_size"
        
        return 0
    else
        print_error "Failed to create database backup"
        return 1
    fi
}

# Function to create schema-only backup
create_schema_backup() {
    local backup_file="$BACKUP_DIR/skema_schema_$TIMESTAMP.sql"
    
    print_status "Creating schema-only backup..."
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --clean --no-owner --no-privileges \
        --schema-only > "$backup_file"; then
        
        gzip "$backup_file"
        print_success "Schema backup created: $backup_file.gz"
        return 0
    else
        print_error "Failed to create schema backup"
        return 1
    fi
}

# Function to create data-only backup
create_data_backup() {
    local backup_file="$BACKUP_DIR/skema_data_$TIMESTAMP.sql"
    
    print_status "Creating data-only backup..."
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --no-owner --no-privileges \
        --data-only --inserts > "$backup_file"; then
        
        gzip "$backup_file"
        print_success "Data backup created: $backup_file.gz"
        return 0
    else
        print_error "Failed to create data backup"
        return 1
    fi
}

# Function to backup specific tables
backup_critical_tables() {
    local tables=("users" "boards" "cards" "calendar_events" "journal_entries")
    local backup_file="$BACKUP_DIR/skema_critical_tables_$TIMESTAMP.sql"
    
    print_status "Creating backup of critical tables..."
    
    local table_args=""
    for table in "${tables[@]}"; do
        table_args="$table_args -t $table"
    done
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --no-owner --no-privileges \
        --data-only --inserts $table_args > "$backup_file"; then
        
        gzip "$backup_file"
        print_success "Critical tables backup created: $backup_file.gz"
        return 0
    else
        print_error "Failed to create critical tables backup"
        return 1
    fi
}

# Function to clean old backups
cleanup_old_backups() {
    print_status "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    while IFS= read -r -d '' file; do
        rm "$file"
        deleted_count=$((deleted_count + 1))
        print_status "Deleted old backup: $(basename "$file")"
    done < <(find "$BACKUP_DIR" -name "skema_*.sql.gz" -type f -mtime +"$RETENTION_DAYS" -print0)
    
    while IFS= read -r -d '' file; do
        rm "$file"
        deleted_count=$((deleted_count + 1))
        print_status "Deleted old backup: $(basename "$file")"
    done < <(find "$BACKUP_DIR" -name "skema_*.custom" -type f -mtime +"$RETENTION_DAYS" -print0)
    
    if [ $deleted_count -gt 0 ]; then
        print_success "Cleaned up $deleted_count old backup files"
    else
        print_status "No old backups to clean up"
    fi
}

# Function to verify backup
verify_backup() {
    local backup_file="$1"
    
    print_status "Verifying backup: $(basename "$backup_file")"
    
    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        # Check if it's a valid gzip file
        if file "$backup_file" | grep -q "gzip compressed"; then
            # Test if we can decompress it
            if zcat "$backup_file" | head -n 1 | grep -q "PostgreSQL database dump"; then
                print_success "Backup verification passed"
                return 0
            fi
        elif file "$backup_file" | grep -q "PostgreSQL custom database dump"; then
            print_success "Custom format backup verification passed"
            return 0
        fi
    fi
    
    print_error "Backup verification failed"
    return 1
}

# Function to create backup manifest
create_manifest() {
    local manifest_file="$BACKUP_DIR/backup_manifest_$TIMESTAMP.json"
    
    print_status "Creating backup manifest..."
    
    cat > "$manifest_file" << EOF
{
    "timestamp": "$TIMESTAMP",
    "database": "$DB_NAME",
    "host": "$DB_HOST",
    "created_at": "$(date -Iseconds)",
    "retention_days": $RETENTION_DAYS,
    "files": [
EOF

    local first=true
    for file in "$BACKUP_DIR"/skema_*_"$TIMESTAMP".sql.gz "$BACKUP_DIR"/skema_*_"$TIMESTAMP".custom; do
        if [ -f "$file" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                echo "," >> "$manifest_file"
            fi
            
            local filename=$(basename "$file")
            local size=$(stat -c%s "$file")
            local checksum=$(sha256sum "$file" | cut -d' ' -f1)
            
            cat >> "$manifest_file" << EOF
        {
            "filename": "$filename",
            "size_bytes": $size,
            "sha256": "$checksum"
        }
EOF
        fi
    done

    cat >> "$manifest_file" << EOF

    ]
}
EOF

    print_success "Backup manifest created: $manifest_file"
}

# Main backup function
main() {
    print_status "Starting Skema database backup process"
    print_status "Timestamp: $TIMESTAMP"
    print_status "Database: $DB_NAME@$DB_HOST:$DB_PORT"
    echo

    # Create backup directory
    create_backup_dir

    # Wait for database to be ready
    if ! wait_for_database; then
        exit 1
    fi

    # Create different types of backups
    local backup_success=true

    if ! create_full_backup; then
        backup_success=false
    fi

    if ! create_schema_backup; then
        backup_success=false
    fi

    if ! create_data_backup; then
        backup_success=false
    fi

    if ! backup_critical_tables; then
        backup_success=false
    fi

    # Verify backups
    for backup_file in "$BACKUP_DIR"/skema_*_"$TIMESTAMP".sql.gz "$BACKUP_DIR"/skema_*_"$TIMESTAMP".custom; do
        if [ -f "$backup_file" ]; then
            if ! verify_backup "$backup_file"; then
                backup_success=false
            fi
        fi
    done

    # Create manifest
    create_manifest

    # Clean up old backups
    cleanup_old_backups

    # Final status
    if [ "$backup_success" = true ]; then
        print_success "Backup process completed successfully!"
        
        # Show backup summary
        echo
        print_status "Backup Summary:"
        ls -lh "$BACKUP_DIR"/skema_*_"$TIMESTAMP".*
        
        # Show total backup directory size
        local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
        print_status "Total backup directory size: $total_size"
        
    else
        print_error "Backup process completed with errors!"
        exit 1
    fi
}

# Handle script interruption
trap 'print_warning "Backup interrupted"; exit 1' INT

# Run main function
main "$@"