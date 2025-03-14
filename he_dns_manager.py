#!/usr/bin/env python3

# Name    : he_dns_manager.py
# Author  : Indranil Das Gupta <indradg@l2c2.co.in>
# Version : 1.1
# License : GNU GPL v3 (or higher)

import argparse
import json
import sys
import requests
from bs4 import BeautifulSoup
import re
import getpass

class HurricaneDNS:
    def __init__(self, username, password, debug=False):
        self.session = requests.Session()
        self.base_url = "https://dns.he.net"
        self.username = username
        self.password = password
        self.logged_in = False
        self.debug = debug
        self.supported_record_types = ['A', 'AAAA']

    def debug_print(self, message):
        """Print message only if debug mode is enabled"""
        if self.debug:
            print(f"DEBUG: {message}")

    def login(self):
        if self.logged_in:
            return True

        try:
            self.debug_print(f"Attempting to login as {self.username}")
            login_url = f"{self.base_url}/"
            
            # First request to get cookies
            initial_response = self.session.get(login_url)
            self.debug_print(f"Initial page load status: {initial_response.status_code}")
            self.debug_print(f"Cookies received: {dict(self.session.cookies)}")
            
            login_data = {
                'email': self.username,
                'pass': self.password,
                'submit': 'Login!'
            }
            
            self.debug_print(f"Submitting login form with fields: {list(login_data.keys())}")
            
            # Important: use the same session to maintain cookies
            login_response = self.session.post(login_url, data=login_data, allow_redirects=True)
            self.debug_print(f"Login response status: {login_response.status_code}")
            self.debug_print(f"Cookies after login: {dict(self.session.cookies)}")
            
            # Simple check for successful login
            self.logged_in = "Incorrect login" not in login_response.text and len(self.session.cookies) > 0
            self.debug_print(f"Login successful: {self.logged_in}")
            
            if not self.logged_in:
                print("Login failed. Response excerpt:")
                print(login_response.text[:1000])
            
            return self.logged_in
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False
			
    def get_zones(self, domain_name=None):
        if not self.login():
            raise Exception("Login failed")
        
        try:
            # Use the correct URL for zones - use index.cgi not index.php
            zones_url = f"{self.base_url}/index.cgi"
            self.debug_print(f"Fetching zones from: {zones_url}")
            self.debug_print(f"Using cookies: {dict(self.session.cookies)}")
            
            response = self.session.get(zones_url)
            self.debug_print(f"Zones response status: {response.status_code}")
            
            # Print the full response for debugging
            if self.debug:
                self.debug_print("\n==== RESPONSE CONTENT START ====")
                self.debug_print(response.text[:500])  # Just show the first 500 chars to avoid too much output
                self.debug_print("==== RESPONSE CONTENT END ====\n")
            
            # Save cookies after the request
            self.debug_print(f"Cookies after zones request: {dict(self.session.cookies)}")
            
            zones = []
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for the domains table - this is the table with ID 'domains_table'
            domains_table = soup.find('table', id='domains_table')
            if domains_table:
                for tr in domains_table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) >= 3:
                        zone_name = tds[2].text.strip()
                        # Find the zone ID from the edit button
                        edit_btn = tr.find('img', alt='edit')
                        if edit_btn and edit_btn.get('onclick'):
                            zone_id_match = re.search(r'hosted_dns_zoneid=(\d+)', edit_btn.get('onclick'))
                            if zone_id_match:
                                zone_id = zone_id_match.group(1)
                                zones.append({'id': zone_id, 'name': zone_name})
            
            # If domain_name is provided, filter for that specific domain
            if domain_name:
                matching_zones = [zone for zone in zones if zone['name'] == domain_name]
                if not matching_zones:
                    print(f"Domain {domain_name} not found in your HE DNS zones.")
                    sys.exit(1)
                return matching_zones[0]  # Return the first matching zone
            
            return zones
        except Exception as e:
            print(f"Error in get_zones: {str(e)}")
            raise
			
    def get_records(self, zone):
        if not self.login():
            raise Exception("Login failed")
        
        try:
            # First, find the zone ID if a name was provided
            zone_id = zone
            if isinstance(zone, dict) and 'id' in zone:
                zone_id = zone['id']
            elif not str(zone).isdigit():
                for z in self.get_zones():
                    if z['name'] == zone:
                        zone_id = z['id']
                        break
            
            # Use correct URL format for records
            records_url = f"{self.base_url}/index.cgi?hosted_dns_zoneid={zone_id}&menu=edit_zone&hosted_dns_editzone"
            self.debug_print(f"Fetching records from: {records_url}")
            self.debug_print(f"Using cookies: {dict(self.session.cookies)}")
            
            response = self.session.get(records_url)
            self.debug_print(f"Records response status: {response.status_code}")
            
            records = []
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all record rows in the table
            for tr in soup.find_all('tr', class_=['dns_tr', 'dns_tr_alt']):
                tds = tr.find_all('td')
                if len(tds) >= 5:  # Make sure there are enough columns
                    record = {}
                    
                    # First, try to get the record ID from the first column's edit/delete links
                    record_id = None
                    first_cell = tds[0] if len(tds) > 0 else None
                    if first_cell:
                        for link in first_cell.find_all('a'):
                            onclick = link.get('onclick', '')
                            match = re.search(r'(?:delete|edit)_record\((\d+)\)', onclick)
                            if match:
                                record_id = match.group(1)
                                break
                    
                    if record_id:
                        record['id'] = record_id
                    
                    # Parse the rest of the record data
                    # CORRECT field mapping based on observation
                    if len(tds) >= 5:
                        record['id'] = tds[1].text.strip()  # HE recordid
                        record['name'] = tds[2].text.strip()                 # FQDN
                        record['type'] = tds[3].text.strip()                 # Record type
                        record['ttl'] = tds[4].text.strip()                  # TTL
                        
                        # Only include A and AAAA records
                        if record['type'] in self.supported_record_types:
                            records.append(record)
            
            return records
        except Exception as e:
            print(f"Error in get_records: {str(e)}")
            raise

    def record_exists(self, zone, record_name, record_type='A'):
        """Check if a record already exists in the zone"""
        if record_type not in self.supported_record_types:
            raise ValueError(f"Unsupported record type: {record_type}. Only {', '.join(self.supported_record_types)} are supported.")
            
        records = self.get_records(zone)
        for record in records:
            if record['name'] == record_name and record['type'] == record_type:
                return record
        return None

    def add_record(self, zone, record_type, name, content, ttl=300, check_exists=True):
        if not self.login():
            raise Exception("Login failed")
        
        if record_type not in self.supported_record_types:
            raise ValueError(f"Unsupported record type: {record_type}. Only {', '.join(self.supported_record_types)} are supported.")
        
        try:
            # Find zone ID if name provided
            zone_id = zone
            if isinstance(zone, dict) and 'id' in zone:
                zone_id = zone['id']
            elif not str(zone).isdigit():
                for z in self.get_zones():
                    if z['name'] == zone:
                        zone_id = z['id']
                        break
            
            # Check if the record already exists
            if check_exists:
                existing_record = self.record_exists(zone_id, name, record_type)
                if existing_record:
                    print(f"Record '{name}' of type '{record_type}' already exists with content '{existing_record['content']}'.")
                    return False
            
            # Use the correct URL format and parameters
            records_url = f"{self.base_url}/?hosted_dns_zoneid={zone_id}&menu=edit_zone&hosted_dns_editzone"
            self.debug_print(f"Adding record to: {records_url}")
            self.debug_print(f"Using cookies: {dict(self.session.cookies)}")
            
            # Prepare data for adding record
            data = {
                'account': '',
                'menu': 'edit_zone',
                'Type': record_type,
                'hosted_dns_zoneid': zone_id,
                'hosted_dns_recordid': '',
                'hosted_dns_editzone': '1',
                'Priority': '',  # Not used for A/AAAA records
                'Name': name,
                'Content': content,
                'TTL': str(ttl),
                'hosted_dns_editrecord': 'Submit'
            }
            
            self.debug_print(f"Submitting record data: {data}")
            response = self.session.post(records_url, data=data)
            self.debug_print(f"Add record response status: {response.status_code}")
            
            # Check if record was added successfully
            success = "successfully added" in response.text.lower() or "record updated" in response.text.lower()
            print(f"Record '{name}' added successfully: {success}")
            
            return success
        except Exception as e:
            print(f"Error in add_record: {str(e)}")
            raise
			
    def delete_record(self, zone, record_id=None, record_name=None, record_type='A', force_delete=False):
        if not self.login():
            raise Exception("Login failed")
        
        if record_type not in self.supported_record_types:
            raise ValueError(f"Unsupported record type: {record_type}. Only {', '.join(self.supported_record_types)} are supported.")
        
        try:
            # Find zone ID if name provided
            zone_id = zone
            if isinstance(zone, dict) and 'id' in zone:
                zone_id = zone['id']
            elif not str(zone).isdigit():
                for z in self.get_zones():
                    if z['name'] == zone:
                        zone_id = z['id']
                        break
            
            # If record_id is not provided but record_name is, try to find the record
            if not record_id and record_name:
                existing_record = self.record_exists(zone_id, record_name, record_type)
                if not existing_record:
                    print(f"Record '{record_name}' not found.")
                    return False
                record_id = existing_record['id']
            
            # Ask for confirmation unless force_delete is True
            if not force_delete:
                confirm = input(f"Are you sure you want to delete record ID {record_id}? (y/N): ")
                if confirm.lower() != 'y':
                    print("Deletion cancelled.")
                    return False
            
            # Use the correct URL format based on the deletion curl example
            delete_url = f"{self.base_url}/index.cgi"
            self.debug_print(f"Deleting record from: {delete_url}")
            self.debug_print(f"Using cookies: {dict(self.session.cookies)}")
            
            # Updated data parameters to match the curl example
            data = {
                'hosted_dns_zoneid': zone_id,
                'hosted_dns_recordid': record_id,
                'menu': 'edit_zone',
                'hosted_dns_delconfirm': 'delete',
                'hosted_dns_editzone': '1',
                'hosted_dns_delrecord': '1'
            }
            
            self.debug_print(f"Submitting delete data: {data}")
            response = self.session.post(delete_url, data=data)
            self.debug_print(f"Delete record response status: {response.status_code}")
            
            # Check if record was deleted successfully
            success = "successfully removed" in response.text.lower() or "successfully deleted" in response.text.lower()
            print(f"Record '{record_name}' deleted successfully: {success}")
            
            return success
        except Exception as e:
            print(f"Error in delete_record: {str(e)}")
            raise
			
def main():
    parser = argparse.ArgumentParser(description='Hurricane Electric DNS Management CLI')
    parser.add_argument('-u', '--username', help='Hurricane Electric username/email')
    parser.add_argument('-p', '--password', help='Hurricane Electric password')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--domain', help='Domain name to operate on (e.g., example.com)')
    parser.add_argument('--zone', help='Zone ID to operate on (alternative to --domain)')
    parser.add_argument('--force-delete', action='store_true', help='Delete records without confirmation')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List zones command
    subparsers.add_parser('list-zones', help='List all zones')
    
    # List records command
    list_records_parser = subparsers.add_parser('list-records', help='List all records for a zone')
    
    # Add subdomain command
    add_subdomain_parser = subparsers.add_parser('add-subdomain', help='Add one or more subdomains')
    add_subdomain_parser.add_argument('subdomains', nargs='+', help='One or more subdomains to add (e.g., test.example.com)')
    add_subdomain_parser.add_argument('--content', help='IP address content')
    add_subdomain_parser.add_argument('--type', choices=['A', 'AAAA'], default='A', help='Record type (default: A)')
    add_subdomain_parser.add_argument('--ttl', type=int, default=300, help='TTL in seconds (default: 300)')
	
    # Delete subdomain command
    delete_subdomain_parser = subparsers.add_parser('delete-subdomain', help='Delete one or more subdomains')
    delete_subdomain_parser.add_argument('subdomains', nargs='+', help='One or more subdomains to delete (e.g., test.example.com)')
    delete_subdomain_parser.add_argument('--type', choices=['A', 'AAAA'], default='A', help='Record type (default: A)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    username = args.username or input("Username: ")
    password = args.password or getpass.getpass("Password: ")
    
    try:
        # Pass the debug flag to the client
        client = HurricaneDNS(username=username, password=password, debug=args.debug)
        
        # If domain is specified, get the zone information
        zone = None
        if args.domain:
            zone = client.get_zones(args.domain)
            print(f"Working with domain: {args.domain} (Zone ID: {zone['id']})")
        if args.command == 'list-zones':
            zones = client.get_zones()
            print("\nZones:")
            print(json.dumps(zones, indent=2))
            sys.exit(0)
            
        elif args.command == 'list-records':
            # If no zone specified via --zone, use the domain specified via --domain
            target_zone = args.zone or (zone['id'] if zone else None)
            if not target_zone:
                print("Error: You must specify either --domain or --zone")
                sys.exit(1)
                
            records = client.get_records(target_zone)
            print("\nRecords:")
            print(json.dumps(records, indent=2))
            sys.exit(0)
            
        elif args.command == 'add-subdomain':
            if not args.domain:
                print("Error: For adding subdomains, you must provide --domain")
                sys.exit(1)
                
            if not args.content:
                print("Error: For adding subdomains, you must provide --content (IP address)")
                sys.exit(1)
                
            # Process each subdomain
            success_count = 0
            for subdomain in args.subdomains:
                # If subdomain doesn't include the domain, add it
                if not subdomain.endswith(args.domain):
                    # Check if it's just the subdomain prefix
                    if '.' not in subdomain:
                        full_name = f"{subdomain}.{args.domain}"
                    else:
                        full_name = subdomain
                else:
                    full_name = subdomain
                
                success = client.add_record(
                    zone=zone['id'] if zone else None,
                    record_type=args.type,
                    name=full_name,
                    content=args.content,
                    ttl=args.ttl
                )
                if success:
                    success_count += 1
            
            if success_count == len(args.subdomains):
                print(f"All {success_count} subdomains added successfully")
                sys.exit(0)
            else:
                print(f"Added {success_count} out of {len(args.subdomains)} subdomains")
                sys.exit(1)
				
        elif args.command == 'delete-subdomain':
            if not args.domain:
                print("Error: For deleting subdomains, you must provide --domain")
                sys.exit(1)
                
            # Process each subdomain
            success_count = 0
            for subdomain in args.subdomains:
                # If subdomain doesn't include the domain, add it
                if not subdomain.endswith(args.domain):
                    # Check if it's just the subdomain prefix
                    if '.' not in subdomain:
                        full_name = f"{subdomain}.{args.domain}"
                    else:
                        full_name = subdomain
                else:
                    full_name = subdomain
                
                success = client.delete_record(
                    zone=zone['id'] if zone else None,
                    record_name=full_name,
                    record_type=args.type,
                    force_delete=args.force_delete
                )
                if success:
                    success_count += 1
            
            if success_count == len(args.subdomains):
                print(f"All {success_count} subdomains deleted successfully")
                sys.exit(0)
            else:
                print(f"Deleted {success_count} out of {len(args.subdomains)} subdomains")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
