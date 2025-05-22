import re
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class KQLValidator:
    """Validates and corrects KQL syntax and common errors"""
    
    def __init__(self):
        # Common KQL operators and functions
        self.kql_operators = {
            'where', 'project', 'extend', 'summarize', 'order', 'sort', 'take', 'limit',
            'join', 'union', 'distinct', 'top', 'sample', 'render', 'let', 'datatable'
        }
        
        self.kql_functions = {
            'count', 'sum', 'avg', 'min', 'max', 'dcount', 'countif', 'sumif',
            'ago', 'now', 'datetime', 'timespan', 'bin', 'floor', 'ceiling',
            'strlen', 'substring', 'split', 'strcat', 'replace', 'trim',
            'tolower', 'toupper', 'contains', 'startswith', 'endswith',
            'isempty', 'isnotempty', 'isnull', 'isnotnull', 'iff', 'case'
        }
        
        self.time_functions = {'ago', 'now', 'datetime', 'timespan', 'bin'}
        
        # Common table names in Log Analytics
        self.common_tables = {
            'SecurityEvent', 'Syslog', 'Event', 'Heartbeat', 'Perf', 'Alert',
            'AzureActivity', 'SigninLogs', 'AuditLogs', 'AppServiceHTTPLogs',
            'ContainerLog', 'KubeEvents', 'InsightsMetrics', 'VMConnection',
            'SecurityAlert', 'SecurityIncident', 'ThreatIntelligenceIndicator',
            'Usage', 'Operation', 'ConfigurationChange', 'ConfigurationData'
        }
    
    def validate_and_correct(self, kql_query: str, available_tables: List[str] = None) -> Tuple[str, List[str], bool]:
        """
        Validate and correct a KQL query
        
        Returns:
            Tuple of (corrected_query, warnings, is_valid)
        """
        warnings = []
        corrected_query = kql_query.strip()
        
        # Remove markdown formatting if present
        corrected_query = self._remove_markdown(corrected_query)
        
        # Basic syntax checks
        corrected_query, syntax_warnings = self._check_basic_syntax(corrected_query)
        warnings.extend(syntax_warnings)
        
        # Check table names
        corrected_query, table_warnings = self._check_table_names(corrected_query, available_tables)
        warnings.extend(table_warnings)
        
        # Check time filters
        corrected_query, time_warnings = self._check_time_filters(corrected_query)
        warnings.extend(time_warnings)
        
        # Check operators and functions
        operator_warnings = self._check_operators_and_functions(corrected_query)
        warnings.extend(operator_warnings)
        
        # Check for common mistakes
        corrected_query, mistake_warnings = self._fix_common_mistakes(corrected_query)
        warnings.extend(mistake_warnings)
        
        # Final validation
        is_valid = self._final_validation(corrected_query)
        
        return corrected_query, warnings, is_valid
    
    def _remove_markdown(self, query: str) -> str:
        """Remove markdown code block formatting"""
        # Remove ```kusto or ```kql blocks
        query = re.sub(r'^```(?:kusto|kql)?\s*\n?', '', query, flags=re.MULTILINE)
        query = re.sub(r'\n?```\s*$', '', query, flags=re.MULTILINE)
        
        # Remove inline code backticks
        query = re.sub(r'^`([^`]+)`$', r'\1', query.strip())
        
        return query.strip()
    
    def _check_basic_syntax(self, query: str) -> Tuple[str, List[str]]:
        """Check basic KQL syntax"""
        warnings = []
        corrected = query
        
        # Check for missing semicolons (not required in KQL but sometimes added)
        if corrected.endswith(';'):
            corrected = corrected[:-1]
            warnings.append("Removed unnecessary semicolon at end of query")
        
        # Check for proper pipe usage
        lines = corrected.split('\n')
        corrected_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # First line should not start with pipe
            if i == 0 and line.startswith('|'):
                line = line[1:].strip()
                warnings.append("Removed unnecessary pipe at beginning of query")
            
            # Other lines should start with pipe (except comments and table names)
            elif i > 0 and line and not line.startswith('|') and not line.startswith('//'):
                # Check if this looks like a continuation of the previous line
                if any(op in line.lower() for op in self.kql_operators):
                    line = '| ' + line
                    warnings.append(f"Added missing pipe before '{line[:20]}...'")
            
            corrected_lines.append(line)
        
        corrected = '\n'.join(corrected_lines)
        
        return corrected, warnings
    
    def _check_table_names(self, query: str, available_tables: List[str] = None) -> Tuple[str, List[str]]:
        """Check and correct table names"""
        warnings = []
        corrected = query
        
        # Extract table names from the query
        table_pattern = r'^([A-Za-z][A-Za-z0-9_]*)\s*(?:\||$)'
        lines = corrected.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('|'):
                continue
                
            match = re.match(table_pattern, line)
            if match:
                table_name = match.group(1)
                
                # Check if table name is valid
                if available_tables:
                    # Use provided table list
                    if table_name not in available_tables:
                        # Try to find a close match
                        close_match = self._find_closest_table(table_name, available_tables)
                        if close_match:
                            corrected = corrected.replace(table_name, close_match, 1)
                            warnings.append(f"Corrected table name '{table_name}' to '{close_match}'")
                        else:
                            warnings.append(f"Table '{table_name}' not found in workspace")
                else:
                    # Use common table names
                    if table_name not in self.common_tables:
                        close_match = self._find_closest_table(table_name, list(self.common_tables))
                        if close_match:
                            corrected = corrected.replace(table_name, close_match, 1)
                            warnings.append(f"Suggested table name correction: '{table_name}' -> '{close_match}'")
        
        return corrected, warnings
    
    def _find_closest_table(self, table_name: str, available_tables: List[str]) -> Optional[str]:
        """Find the closest matching table name"""
        table_lower = table_name.lower()
        
        # Exact match (case insensitive)
        for table in available_tables:
            if table.lower() == table_lower:
                return table
        
        # Partial match
        for table in available_tables:
            if table_lower in table.lower() or table.lower() in table_lower:
                return table
        
        # Levenshtein distance (simple version)
        min_distance = float('inf')
        closest_table = None
        
        for table in available_tables:
            distance = self._levenshtein_distance(table_lower, table.lower())
            if distance < min_distance and distance <= 2:  # Allow up to 2 character differences
                min_distance = distance
                closest_table = table
        
        return closest_table
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _check_time_filters(self, query: str) -> Tuple[str, List[str]]:
        """Check and correct time filters"""
        warnings = []
        corrected = query
        
        # Check for common time filter patterns
        time_patterns = [
            (r'ago\s*\(\s*(\d+)\s*\)', r'ago(\1d)'),  # ago(7) -> ago(7d)
            (r'ago\s*\(\s*(\d+)\s*days?\s*\)', r'ago(\1d)'),  # ago(7 days) -> ago(7d)
            (r'ago\s*\(\s*(\d+)\s*hours?\s*\)', r'ago(\1h)'),  # ago(24 hours) -> ago(24h)
            (r'ago\s*\(\s*(\d+)\s*minutes?\s*\)', r'ago(\1m)'),  # ago(30 minutes) -> ago(30m)
        ]
        
        for pattern, replacement in time_patterns:
            if re.search(pattern, corrected, re.IGNORECASE):
                corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
                warnings.append("Corrected time filter format")
        
        # Check for missing TimeGenerated filter
        if 'TimeGenerated' not in corrected and 'ago(' not in corrected.lower():
            warnings.append("Consider adding a TimeGenerated filter for better performance")
        
        return corrected, warnings
    
    def _check_operators_and_functions(self, query: str) -> List[str]:
        """Check operators and functions usage"""
        warnings = []
        query_lower = query.lower()
        
        # Check for common operator mistakes
        if 'order by' in query_lower and 'sort by' in query_lower:
            warnings.append("Use either 'order by' or 'sort by', not both")
        
        if 'take' in query_lower and 'limit' in query_lower:
            warnings.append("Use either 'take' or 'limit', not both")
        
        # Check for missing aggregation in summarize
        if 'summarize' in query_lower:
            if not any(func in query_lower for func in ['count()', 'sum(', 'avg(', 'min(', 'max(', 'dcount(']):
                warnings.append("Summarize statement should include aggregation functions")
        
        # Check for project after summarize
        lines = query.split('\n')
        has_summarize = False
        for line in lines:
            line_lower = line.lower().strip()
            if 'summarize' in line_lower:
                has_summarize = True
            elif has_summarize and 'project' in line_lower:
                warnings.append("Project after summarize may not work as expected; consider using extend instead")
                break
        
        return warnings
    
    def _fix_common_mistakes(self, query: str) -> Tuple[str, List[str]]:
        """Fix common KQL mistakes"""
        warnings = []
        corrected = query
        
        # Fix common function name mistakes
        function_fixes = {
            'length(': 'strlen(',
            'len(': 'strlen(',
            'substring(': 'substr(',
            'isnull(': 'isempty(',
            'notnull(': 'isnotempty(',
        }
        
        for wrong, correct in function_fixes.items():
            if wrong in corrected.lower():
                corrected = re.sub(re.escape(wrong), correct, corrected, flags=re.IGNORECASE)
                warnings.append(f"Corrected function name: {wrong} -> {correct}")
        
        # Fix common operator mistakes
        operator_fixes = {
            ' = ': ' == ',  # Assignment vs comparison
            'and ': 'and ',  # Ensure proper spacing
            'or ': 'or ',
        }
        
        # Fix string comparison operators
        if re.search(r'\w+\s*=\s*"[^"]*"', corrected):
            corrected = re.sub(r'(\w+)\s*=\s*("[^"]*")', r'\1 == \2', corrected)
            warnings.append("Changed assignment operator (=) to comparison operator (==) for string comparison")
        
        return corrected, warnings
    
    def _final_validation(self, query: str) -> bool:
        """Perform final validation checks"""
        # Check for basic structure
        if not query.strip():
            return False
        
        # Check for at least one table reference
        lines = [line.strip() for line in query.split('\n') if line.strip()]
        if not lines:
            return False
        
        # First non-comment line should be a table name or union
        first_line = None
        for line in lines:
            if not line.startswith('//'):
                first_line = line
                break
        
        if not first_line:
            return False
        
        # Check if first line looks like a table name or valid KQL start
        if not (re.match(r'^[A-Za-z][A-Za-z0-9_]*', first_line) or 
                first_line.lower().startswith('union') or
                first_line.lower().startswith('let')):
            return False
        
        # Check for balanced parentheses
        open_parens = query.count('(')
        close_parens = query.count(')')
        if open_parens != close_parens:
            return False
        
        return True
    
    def get_query_complexity_score(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity and provide metrics"""
        query_lower = query.lower()
        
        # Count different types of operations
        operations = {
            'filters': query_lower.count('where'),
            'projections': query_lower.count('project'),
            'aggregations': query_lower.count('summarize'),
            'joins': query_lower.count('join'),
            'unions': query_lower.count('union'),
            'sorts': query_lower.count('order by') + query_lower.count('sort by'),
            'limits': query_lower.count('take') + query_lower.count('limit'),
        }
        
        # Calculate complexity score
        complexity_score = sum(operations.values())
        
        # Estimate performance impact
        performance_impact = "Low"
        if complexity_score > 5:
            performance_impact = "High"
        elif complexity_score > 2:
            performance_impact = "Medium"
        
        return {
            "operations": operations,
            "complexity_score": complexity_score,
            "performance_impact": performance_impact,
            "line_count": len([line for line in query.split('\n') if line.strip()]),
            "has_time_filter": 'ago(' in query_lower or 'timegenerated' in query_lower
        } 