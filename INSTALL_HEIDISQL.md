# Installing and Running HeidiSQL on Ubuntu

## Current Status

HeidiSQL is installed via Snap as `heidisql-wine` (runs through Wine compatibility layer).

## How to Launch

### Method 1: Command Line

```bash
heidisql-wine
```

Or:

```bash
snap run heidisql-wine
```

### Method 2: With Display (if running in VNC/remote)

```bash
DISPLAY=:1 heidisql-wine
```

### Method 3: Create Desktop Shortcut

If it doesn't appear in your application menu, create a launcher:

```bash
cat > ~/.local/share/applications/heidisql.desktop << 'EOF'
[Desktop Entry]
Name=HeidiSQL
GenericName=Database Client
Comment=HeidiSQL database management tool
Exec=heidisql-wine
Icon=heidisql-wine
Terminal=false
Type=Application
Categories=Database;Development;
EOF
```

Then refresh the menu:
```bash
update-desktop-database ~/.local/share/applications/
```

## Troubleshooting

### If HeidiSQL doesn't start:

1. **Check Wine is working:**
   ```bash
   wine --version
   ```

2. **Check snap permissions:**
   ```bash
   snap connections heidisql-wine
   ```

3. **Try running with verbose output:**
   ```bash
   snap run heidisql-wine --verbose
   ```

4. **Check if it's a display issue (VNC/X11):**
   ```bash
   echo $DISPLAY
   export DISPLAY=:1  # or :0, depending on your setup
   heidisql-wine
   ```

### Alternative: Install via Wine directly

If snap version doesn't work, you can install HeidiSQL manually via Wine:

```bash
# Install Wine
sudo apt update
sudo apt install wine64

# Download HeidiSQL installer
wget https://www.heidisql.com/installers/HeidiSQL_12.8_64_Portable.zip

# Extract and run
unzip HeidiSQL_12.8_64_Portable.zip
cd HeidiSQL_12.8_64_Portable
wine heidisql.exe
```

## Better Alternatives for PostgreSQL on Linux

Since you're working with PostgreSQL, consider these native Linux tools:

### 1. **DBeaver** (Recommended - Free, Cross-platform)

```bash
# Install via snap
sudo snap install dbeaver-ce

# Or download from: https://dbeaver.io/download/
```

**Advantages:**
- Native Linux app (no Wine)
- Excellent PostgreSQL support
- Free and open source
- Works great with Railway databases

### 2. **pgAdmin 4** (PostgreSQL-specific)

```bash
sudo apt update
sudo apt install pgadmin4
```

**Advantages:**
- Official PostgreSQL tool
- Native Linux
- Excellent for PostgreSQL

### 3. **TablePlus** (Modern, paid but has free tier)

```bash
# Download from: https://tableplus.com/linux
```

### 4. **Command Line: psql** (What you're already using)

For quick queries, `psql` is excellent:

```bash
psql $DATABASE_URL
```

## Connecting to Railway PostgreSQL

Once HeidiSQL (or alternative) is running:

1. **Connection Type:** PostgreSQL
2. **Host:** `shuttle.proxy.rlwy.net`
3. **Port:** `20893`
4. **User:** `postgres`
5. **Password:** (from your Railway DATABASE_URL)
6. **Database:** `railway`

**Important:** When querying DocParser tables, use schema prefix:
```sql
SELECT * FROM docparser.jobs;
```

Not:
```sql
SELECT * FROM jobs;  -- This looks in public schema
```

## Quick Test

To verify HeidiSQL can connect:

1. Launch: `heidisql-wine`
2. Click "New" connection
3. Select "PostgreSQL"
4. Enter Railway connection details
5. Click "Open"

If connection fails, check:
- Railway database is running
- Firewall allows connection
- Credentials are correct

