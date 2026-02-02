"""
sql_validator.py

SQL Security Validator
Validate SQL queries sebelum execution untuk prevent SQL injection
"""

import re
from database_schema import get_allowed_tables


def validate_sql_security(sql: str) -> dict:
    """
    Comprehensive SQL security validation
    
    Returns:
        {
            'valid': bool,
            'errors': list,
            'warnings': list,
            'sanitized_sql': str
        }
    """
    
    errors = []
    warnings = []
    sql_upper = sql.upper().strip()
    
    print("\n" + "=" * 60)
    print("🔒 SQL SECURITY VALIDATION")
    print("=" * 60)
    
    # ==========================================
    # CRITICAL SECURITY CHECKS
    # ==========================================
    
    # Check 1: Must start with SELECT
    if not sql_upper.startswith('SELECT'):
        errors.append("Only SELECT queries are allowed")
    
    # Check 2: Forbidden dangerous commands
    dangerous_commands = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE',
        'EXEC', 'EXECUTE', 'LOAD_FILE', 'OUTFILE', 'DUMPFILE',
        'GRANT', 'REVOKE', 'CREATE', 'REPLACE', 'RENAME',
        'HANDLER', 'CALL', 'PREPARE', 'DEALLOCATE'
    ]
    
    for cmd in dangerous_commands:
        if re.search(rf'\b{cmd}\b', sql_upper):
            errors.append(f"Forbidden command detected: {cmd}")
    
    # Check 3: SQL injection patterns
    injection_patterns = [
        r';\s*DROP',  # ; DROP TABLE
        r'--\s*\w+',  # SQL comments for injection
        r'/\*.*\*/',  # Multi-line comments
        r'UNION\s+SELECT.*FROM',  # UNION-based injection
        r'OR\s+1\s*=\s*1',  # Classic injection
        r'OR\s+TRUE',  # Boolean injection
        r'\'\s*OR\s*\'',  # Quote-based injection
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            errors.append(f"Potential SQL injection pattern detected: {pattern}")
    
    # Check 4: Must have FROM clause
    if 'FROM' not in sql_upper:
        errors.append("Query must contain FROM clause")
    
    # Check 5: Table whitelist validation
    allowed_tables = [t.upper() for t in get_allowed_tables()]
    has_valid_table = False
    
    for table in allowed_tables:
        if re.search(rf'\b{table}\b', sql_upper):
            has_valid_table = True
            break
    
    if not has_valid_table:
        errors.append(f"Query must use tables from allowed list: {', '.join(get_allowed_tables())}")
    
    # ==========================================
    # BEST PRACTICE CHECKS (Warnings)
    # ==========================================
    
    # Warning 1: SELECT * usage
    if re.search(r'SELECT\s+\*', sql_upper):
        warnings.append("Using SELECT * is not recommended. Specify columns explicitly.")
    
    # Warning 2: Missing is_deleted filter for spk/jaringan
    if 'SPK' in sql_upper and 'IS_DELETED' not in sql_upper:
        warnings.append("SPK query should include 'WHERE is_deleted = 0'")
    
    if 'JARINGAN' in sql_upper and 'IS_DELETED' not in sql_upper:
        warnings.append("JARINGAN query should include 'WHERE is_deleted = 0'")
    
    # Warning 3: Missing LIMIT for potentially large results
    if 'LIMIT' not in sql_upper and 'COUNT' not in sql_upper:
        if any(kw in sql_upper for kw in ['SELECT', 'JOIN']):
            warnings.append("Consider adding LIMIT clause to prevent large result sets")
    
    # Warning 4: Missing ORDER BY for list queries
    if 'ORDER BY' not in sql_upper:
        if re.search(r'SELECT\s+\w+.*FROM\s+spk', sql_upper, re.IGNORECASE):
            warnings.append("Consider adding ORDER BY tanggal_spk DESC for SPK queries")
    
    # ==========================================
    # SANITIZATION (Basic cleanup)
    # ==========================================
    
    sanitized_sql = sql.strip()
    
    # Remove trailing semicolons (for consistency)
    sanitized_sql = sanitized_sql.rstrip(';')
    
    # Normalize whitespace
    sanitized_sql = ' '.join(sanitized_sql.split())
    
    # ==========================================
    # RESULT
    # ==========================================
    
    is_valid = len(errors) == 0
    
    if is_valid:
        print(" SQL validation PASSED")
        if warnings:
            print(f"⚠️  {len(warnings)} warning(s):")
            for w in warnings:
                print(f"   - {w}")
    else:
        print(f" SQL validation FAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"   - {e}")
    
    print("=" * 60)
    print()
    
    return {
        'valid': is_valid,
        'errors': errors,
        'warnings': warnings,
        'sanitized_sql': sanitized_sql if is_valid else None
    }


def quick_validate(sql: str) -> bool:
    """
    Quick validation untuk checking saja (return bool)
    """
    result = validate_sql_security(sql)
    return result['valid']


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Test cases
    test_cases = [
        {
            'name': 'Valid SELECT query',
            'sql': "SELECT * FROM spk WHERE no_jaringan = '2021242440' AND is_deleted = 0",
            'should_pass': True
        },
        {
            'name': 'SQL Injection attempt',
            'sql': "SELECT * FROM spk WHERE no_jaringan = '123'; DROP TABLE spk; --",
            'should_pass': False
        },
        {
            'name': 'UPDATE attempt',
            'sql': "UPDATE spk SET is_deleted = 1 WHERE id_spk = 1",
            'should_pass': False
        },
        {
            'name': 'UNION injection',
            'sql': "SELECT * FROM spk UNION SELECT * FROM users",
            'should_pass': False
        },
        {
            'name': 'Valid COUNT query',
            'sql': "SELECT COUNT(*) as total FROM spk WHERE is_deleted = 0",
            'should_pass': True
        },
        {
            'name': 'Invalid table',
            'sql': "SELECT * FROM unknown_table WHERE id = 1",
            'should_pass': False
        }
    ]
    
    print("\n" + "=" * 80)
    print("🧪 SQL VALIDATOR TEST SUITE")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"SQL: {test['sql']}")
        print(f"Expected: {'PASS' if test['should_pass'] else 'FAIL'}")
        
        result = validate_sql_security(test['sql'])
        actual_pass = result['valid']
        
        if actual_pass == test['should_pass']:
            print(" TEST PASSED")
            passed += 1
        else:
            print(" TEST FAILED")
            print(f"   Expected: {test['should_pass']}, Got: {actual_pass}")
            if result['errors']:
                print(f"   Errors: {result['errors']}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)