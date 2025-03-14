# Hurricane Electric DNS Manager

A command-line tool for managing DNS records on Hurricane Electric's Free DNS service.

## Overview

`he_dns_manager.py` is a Python-based CLI tool that allows you to manage A and AAAA DNS records on Hurricane Electric DNS for already setup zones (aka domains). The tool makes it easy to automate DNS record management without using the web interface.

## Features

- List all DNS zones in your Hurricane Electric account
- List all A and AAAA records for a specific domain
- Add one or more A or AAAA records (subdomains) in a single command
- Delete one or more A or AAAA records
- Handles TTL settings with a sensible default (300 seconds)

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - requests
  - beautifulsoup4

## Installation

1. Clone this repository or download the script:

```bash
git clone https://github.com/yourusername/he_dns_manager.git
cd he_dns_manager
```

2. Install required dependencies:

```bash
pip install requests beautifulsoup4
```

3. Make the script executable:

```bash
chmod +x he_dns_manager.py
```

## Usage

### Basic Syntax

```bash
python he_dns_manager.py [options] <command> [command-options]
```

### Authentication

You can provide authentication credentials in several ways:

1. Using command-line arguments:
```bash
python he_dns_manager.py -u username@example.com -p password <command>
```

2. When prompted (more secure):
```bash
python he_dns_manager.py <command>
Username: username@example.com
Password: [hidden input]
```

### Commands

#### List DNS Zones

Lists all domains (zones) in your Hurricane Electric account:

```bash
python he_dns_manager.py list-zones
```

#### List Records

Lists all A and AAAA records for a specific domain:

```bash
python he_dns_manager.py --domain example.com list-records
```

Or by zone ID:

```bash
python he_dns_manager.py list-records --zone 123456
```

#### Add Subdomains

Add one or more A record subdomains:

```bash
python he_dns_manager.py --domain example.com add-subdomain test1 test2 --content 192.168.1.1
```

Add an AAAA record with custom TTL:

```bash
python he_dns_manager.py --domain example.com add-subdomain ipv6test --type AAAA --content 2001:db8::1 --ttl 3600
```

#### Delete Subdomains

Delete one or more subdomains (with confirmation):

```bash
python he_dns_manager.py --domain example.com delete-subdomain test1 test2
```

Delete without confirmation:

```bash
python he_dns_manager.py --domain example.com delete-subdomain test1 --force-delete
```

### Options

| Option | Description |
|--------|-------------|
| `-u`, `--username` | Hurricane Electric username/email |
| `-p`, `--password` | Hurricane Electric password |
| `-d`, `--debug` | Enable debug output |
| `--domain` | Domain name to operate on (e.g., example.com) |
| `--force-delete` | Delete records without confirmation |

### Subdomain Command Options

#### For `add-subdomain`:

| Option | Description |
|--------|-------------|
| `--content` | IP address content (required) |
| `--type` | Record type: 'A' (default) or 'AAAA' |
| `--ttl` | Time-to-live in seconds (default: 300) |

#### For `delete-subdomain`:

| Option | Description |
|--------|-------------|
| `--type` | Record type: 'A' (default) or 'AAAA' |

## Examples

### Basic Operations

1. Add multiple A record subdomains with default TTL:
```bash
python he_dns_manager.py --domain example.com add-subdomain staging dev test --content 192.168.1.1
```

2. Add an AAAA record:
```bash
python he_dns_manager.py --domain example.com add-subdomain ipv6-server --type AAAA --content 2001:db8::1
```

3. Delete multiple subdomains in one command:
```bash
python he_dns_manager.py --domain example.com delete-subdomain old-server backup-server --force-delete
```

### Structured Subdomain Names

You can add structured subdomains like this:

```bash
python he_dns_manager.py --domain example.com add-subdomain api.staging web.staging --content 192.168.2.1
```

This will create `api.staging.example.com` and `web.staging.example.com`.

## Troubleshooting

### Login Issues

If you're having trouble logging in:

1. Verify your username and password
2. Run with debug mode: `python he_dns_manager.py -d list-zones`
3. Check if HE might have changed their login form

### Record Management Issues

1. If records aren't showing up, check if they are of type A or AAAA (the only supported types)
2. Verify domain ownership and permissions in your HE account
3. Run with debug mode to see detailed request and response information

## Security Notes

- Avoid using username/password on the command line in production environments
- The script does not store credentials
- Consider using environment variables or a credentials file for automation

## License

GNU GPL v3 (or higher)

## Author

Indranil Das Gupta <indradg@l2c2.co.in>
