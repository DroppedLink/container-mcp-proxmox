#!/usr/bin/env python3
"""
Quick test for new Proxmox MCP tools
"""

import asyncio
import os
import sys

# Add the current directory to Python path for src imports
sys.path.append(os.path.dirname(__file__))

try:
    from src.unified_service import ProxmoxService
except ImportError:
    print("❌ Error: Cannot import ProxmoxService")
    sys.exit(1)

async def test_new_tools():
    """Test the new tools we added."""
    print("🚀 Quick Test for New Proxmox MCP Tools")
    print("=" * 50)
    
    # Check environment variables
    host = os.getenv('PROXMOX_HOST')
    user = os.getenv('PROXMOX_USER')
    password = os.getenv('PROXMOX_PASSWORD')
    
    if not all([host, user, password]):
        print("❌ Missing environment variables")
        return False
    
    print(f"🔗 Connecting to Proxmox: {host}")
    
    try:
        service = ProxmoxService(host, user, password)
        print("✅ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Get a test node
    try:
        resources = await service.list_resources()
        if not resources.get('resources'):
            print("❌ No resources found")
            return False
        
        test_node = resources['resources'][0]['node']
        print(f"📍 Using test node: {test_node}")
        
    except Exception as e:
        print(f"❌ Failed to get resources: {e}")
        return False
    
    # Test new tools
    tests = [
        ("Storage Management", [
            ("list_storage", lambda: service.list_storage()),
            ("get_suitable_storage", lambda: service.get_suitable_storage(test_node, "images")),
        ]),
        ("Task Management", [
            ("list_tasks", lambda: service.list_tasks(node=test_node, limit=5)),
            ("list_backup_jobs", lambda: service.list_backup_jobs(node=test_node)),
        ]),
        ("Cluster Management", [
            ("get_cluster_health", lambda: service.get_cluster_health()),
            ("list_cluster_resources", lambda: service.list_cluster_resources()),
            ("get_cluster_config", lambda: service.get_cluster_config()),
        ]),
        ("Performance Monitoring", [
            ("get_node_stats", lambda: service.get_node_stats(test_node)),
            ("list_alerts", lambda: service.list_alerts(node=test_node)),
            ("get_resource_usage", lambda: service.get_resource_usage(node=test_node)),
        ]),
        ("Network Management", [
            ("list_networks", lambda: service.list_networks(node=test_node)),
            ("get_node_network", lambda: service.get_node_network(test_node)),
            ("list_firewall_rules", lambda: service.list_firewall_rules(node=test_node)),
        ]),
    ]
    
    total_tests = sum(len(category_tests) for _, category_tests in tests)
    passed = 0
    
    for category, category_tests in tests:
        print(f"\n📂 {category}")
        print("-" * 30)
        
        for test_name, test_func in category_tests:
            try:
                result = await test_func()
                print(f"  ✅ {test_name}: Success")
                # Print a small sample of the result
                if isinstance(result, dict):
                    keys = list(result.keys())[:3]
                    sample = {k: result[k] for k in keys if k in result}
                    print(f"     Sample: {sample}")
                passed += 1
                
            except Exception as e:
                print(f"  ❌ {test_name}: Failed - {e}")
            
            await asyncio.sleep(0.1)  # Small delay
    
    print(f"\n🎯 Results: {passed}/{total_tests} tests passed ({passed/total_tests*100:.1f}%)")
    
    if passed == total_tests:
        print("🎉 All new tools are working correctly!")
        return True
    else:
        print("⚠️  Some tools need attention")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_new_tools())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1) 