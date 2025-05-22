from typing import List, Dict, Any, Optional
import logging
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

class SchemaRefiner:
    """Refines and processes retrieved schema information for optimal KQL generation"""
    
    def __init__(self):
        self.max_fields_per_table = 15
        self.max_sample_values = 5
        self.priority_fields = [
            "TimeGenerated", "Computer", "SourceSystem", "Type", "Category",
            "EventID", "Level", "LogLevel", "Severity", "Status", "State",
            "UserName", "User", "Account", "IPAddress", "SourceIP", "DestinationIP",
            "ProcessName", "CommandLine", "FileName", "FilePath", "Message"
        ]
    
    def refine_context(self, 
                      natural_language: str,
                      relevant_fields: List[Dict[str, Any]],
                      relevant_values: List[Dict[str, Any]],
                      relevant_schemas: List[Dict[str, Any]],
                      similar_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Refine all retrieved context into a structured format for KQL generation"""
        
        # Group fields by table
        fields_by_table = defaultdict(list)
        for field in relevant_fields:
            fields_by_table[field['table_name']].append(field)
        
        # Group values by table
        values_by_table = defaultdict(list)
        for value in relevant_values:
            values_by_table[value['table_name']].append(value)
        
        # Process and prioritize tables
        refined_tables = self._prioritize_and_refine_tables(
            fields_by_table, values_by_table, relevant_schemas, natural_language
        )
        
        # Extract relevant patterns from similar queries
        query_patterns = self._extract_query_patterns(similar_queries, natural_language)
        
        # Generate refined instructions
        instructions = self._generate_refined_instructions(
            natural_language, refined_tables, query_patterns
        )
        
        return {
            "refined_tables": refined_tables,
            "query_patterns": query_patterns,
            "instructions": instructions,
            "context_summary": self._generate_context_summary(refined_tables, query_patterns)
        }
    
    def _prioritize_and_refine_tables(self, 
                                    fields_by_table: Dict[str, List[Dict[str, Any]]],
                                    values_by_table: Dict[str, List[Dict[str, Any]]],
                                    schemas: List[Dict[str, Any]],
                                    natural_language: str) -> List[Dict[str, Any]]:
        """Prioritize and refine table information"""
        
        refined_tables = []
        nl_lower = natural_language.lower()
        
        # Create schema lookup
        schema_lookup = {schema['table_name']: schema for schema in schemas}
        
        # Process each table
        for table_name, fields in fields_by_table.items():
            table_info = {
                "table_name": table_name,
                "description": schema_lookup.get(table_name, {}).get('description', ''),
                "priority_score": self._calculate_table_priority(table_name, fields, nl_lower),
                "fields": self._prioritize_fields(fields, nl_lower),
                "sample_values": self._get_relevant_values(table_name, values_by_table, nl_lower)
            }
            refined_tables.append(table_info)
        
        # Sort tables by priority
        refined_tables.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Limit to top tables
        return refined_tables[:5]
    
    def _calculate_table_priority(self, table_name: str, fields: List[Dict[str, Any]], nl_lower: str) -> float:
        """Calculate priority score for a table based on relevance to the query"""
        score = 0.0
        
        # Table name relevance
        table_lower = table_name.lower()
        if any(keyword in table_lower for keyword in ['security', 'event', 'log', 'audit']):
            score += 1.0
        
        # Check if table name appears in natural language
        if table_lower in nl_lower:
            score += 2.0
        
        # Field relevance
        for field in fields:
            field_name_lower = field['field_name'].lower()
            if field_name_lower in nl_lower:
                score += 1.5
            if field_name_lower in [pf.lower() for pf in self.priority_fields]:
                score += 0.5
        
        # Common log tables get slight boost
        common_tables = ['securityevent', 'syslog', 'event', 'azureactivity', 'signinlogs']
        if table_lower in common_tables:
            score += 0.5
        
        return score
    
    def _prioritize_fields(self, fields: List[Dict[str, Any]], nl_lower: str) -> List[Dict[str, Any]]:
        """Prioritize and limit fields for a table"""
        
        # Calculate field scores
        for field in fields:
            field['priority_score'] = self._calculate_field_priority(field, nl_lower)
        
        # Sort by priority
        fields.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Ensure priority fields are included
        priority_fields_included = set()
        final_fields = []
        
        for field in fields:
            if len(final_fields) >= self.max_fields_per_table:
                break
            
            field_name_lower = field['field_name'].lower()
            
            # Always include TimeGenerated if available
            if field_name_lower == 'timegenerated':
                final_fields.insert(0, field)
                priority_fields_included.add(field_name_lower)
                continue
            
            # Include high-priority fields
            if (field_name_lower in [pf.lower() for pf in self.priority_fields] and 
                field_name_lower not in priority_fields_included):
                final_fields.append(field)
                priority_fields_included.add(field_name_lower)
            elif field['priority_score'] > 0.5:
                final_fields.append(field)
        
        return final_fields
    
    def _calculate_field_priority(self, field: Dict[str, Any], nl_lower: str) -> float:
        """Calculate priority score for a field"""
        score = 0.0
        field_name_lower = field['field_name'].lower()
        
        # Direct mention in natural language
        if field_name_lower in nl_lower:
            score += 3.0
        
        # Priority fields
        if field_name_lower in [pf.lower() for pf in self.priority_fields]:
            score += 2.0
        
        # Common useful fields
        useful_keywords = ['user', 'computer', 'process', 'file', 'ip', 'address', 'message', 'event', 'error', 'status']
        if any(keyword in field_name_lower for keyword in useful_keywords):
            score += 1.0
        
        # Field description relevance
        description_lower = field.get('description', '').lower()
        if any(word in description_lower for word in nl_lower.split() if len(word) > 3):
            score += 0.5
        
        return score
    
    def _get_relevant_values(self, table_name: str, values_by_table: Dict[str, List[Dict[str, Any]]], nl_lower: str) -> List[Dict[str, Any]]:
        """Get relevant sample values for a table"""
        table_values = values_by_table.get(table_name, [])
        
        relevant_values = []
        for value_info in table_values:
            # Check if any sample values are mentioned in the query
            sample_values = value_info.get('sample_values', [])
            relevant_samples = []
            
            for sample in sample_values[:self.max_sample_values]:
                sample_lower = str(sample).lower()
                if any(word in sample_lower for word in nl_lower.split() if len(word) > 2):
                    relevant_samples.append(sample)
            
            if relevant_samples or len(relevant_values) < 3:
                relevant_values.append({
                    "field_name": value_info['field_name'],
                    "sample_values": relevant_samples or sample_values[:self.max_sample_values]
                })
        
        return relevant_values[:5]  # Limit to 5 fields with values
    
    def _extract_query_patterns(self, similar_queries: List[Dict[str, Any]], natural_language: str) -> List[Dict[str, Any]]:
        """Extract useful patterns from similar queries"""
        patterns = []
        
        for query_info in similar_queries[:3]:  # Top 3 similar queries
            kql_query = query_info.get('kql_query', '')
            nl_query = query_info.get('natural_language', '')
            
            # Extract common KQL patterns
            pattern_info = {
                "similar_nl": nl_query,
                "kql_query": kql_query,
                "patterns": self._identify_kql_patterns(kql_query),
                "relevance_score": self._calculate_query_relevance(nl_query, natural_language)
            }
            patterns.append(pattern_info)
        
        # Sort by relevance
        patterns.sort(key=lambda x: x['relevance_score'], reverse=True)
        return patterns
    
    def _identify_kql_patterns(self, kql_query: str) -> List[str]:
        """Identify common KQL patterns in a query"""
        patterns = []
        kql_lower = kql_query.lower()
        
        # Common KQL operators and functions
        if 'where' in kql_lower:
            patterns.append('filtering')
        if 'summarize' in kql_lower:
            patterns.append('aggregation')
        if 'project' in kql_lower:
            patterns.append('column_selection')
        if 'join' in kql_lower:
            patterns.append('table_join')
        if 'extend' in kql_lower:
            patterns.append('calculated_fields')
        if 'order by' in kql_lower or 'sort by' in kql_lower:
            patterns.append('sorting')
        if 'take' in kql_lower or 'limit' in kql_lower:
            patterns.append('limiting')
        if 'ago(' in kql_lower:
            patterns.append('time_filtering')
        if 'count()' in kql_lower:
            patterns.append('counting')
        
        return patterns
    
    def _calculate_query_relevance(self, similar_nl: str, target_nl: str) -> float:
        """Calculate relevance score between two natural language queries"""
        similar_words = set(similar_nl.lower().split())
        target_words = set(target_nl.lower().split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'show', 'get', 'find'}
        similar_words -= stop_words
        target_words -= stop_words
        
        if not target_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = similar_words & target_words
        union = similar_words | target_words
        
        return len(intersection) / len(union) if union else 0.0
    
    def _generate_refined_instructions(self, 
                                     natural_language: str,
                                     refined_tables: List[Dict[str, Any]],
                                     query_patterns: List[Dict[str, Any]]) -> str:
        """Generate refined instructions for KQL generation"""
        
        instructions = []
        
        # Basic instruction
        instructions.append("Generate a valid KQL query based on the following context:")
        
        # Table information
        if refined_tables:
            instructions.append("\nAvailable Tables:")
            for table in refined_tables[:3]:  # Top 3 tables
                table_desc = f"- {table['table_name']}: {table['description'][:100]}..."
                instructions.append(table_desc)
                
                # Key fields
                key_fields = [f['field_name'] for f in table['fields'][:5]]
                if key_fields:
                    instructions.append(f"  Key fields: {', '.join(key_fields)}")
        
        # Query patterns
        if query_patterns:
            instructions.append("\nSimilar Query Patterns:")
            for pattern in query_patterns[:2]:
                if pattern['patterns']:
                    instructions.append(f"- Uses: {', '.join(pattern['patterns'])}")
        
        # Specific guidance
        instructions.append("\nGuidelines:")
        instructions.append("- Always include TimeGenerated field when available")
        instructions.append("- Use appropriate time filters (e.g., ago(1d), ago(7d))")
        instructions.append("- Only project fields that exist in the schema")
        instructions.append("- Use proper KQL syntax and operators")
        
        return "\n".join(instructions)
    
    def _generate_context_summary(self, refined_tables: List[Dict[str, Any]], query_patterns: List[Dict[str, Any]]) -> str:
        """Generate a concise summary of the context"""
        summary_parts = []
        
        if refined_tables:
            table_names = [table['table_name'] for table in refined_tables[:3]]
            summary_parts.append(f"Tables: {', '.join(table_names)}")
        
        if query_patterns:
            all_patterns = set()
            for pattern in query_patterns:
                all_patterns.update(pattern['patterns'])
            if all_patterns:
                summary_parts.append(f"Patterns: {', '.join(list(all_patterns)[:5])}")
        
        return " | ".join(summary_parts) 