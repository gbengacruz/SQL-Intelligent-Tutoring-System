"""
Enhanced SQL Intelligent Tutoring System with Ontology Integration - by Cruz Bello
A comprehensive rule-based ontology approach for teaching SQL query building
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Token, Comparison, Parenthesis, Function
from sqlparse.tokens import Keyword, DML, Name, Number, String, Operator, Comparison, Punctuation
import re
import sqlite3
from datetime import datetime
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal
from rdflib.plugins.sparql import prepareQuery
import os

class OntologyManager:
    """Manages loading and querying the SQL Tutor Ontology"""
    
    def __init__(self, ontology_file="sql_tutor_ontology.owl"):
        self.graph = Graph()
        self.ontology_file = ontology_file
        self.SQLTUTOR = Namespace("http://www.semanticweb.org/sqltutor/ontology#")
        self.graph.bind("sqltutor", self.SQLTUTOR)
        
        self._load_ontology()
        self._extract_knowledge()
    
    def _load_ontology(self):
        """Load the OWL ontology file"""
        if os.path.exists(self.ontology_file):
            try:
                self.graph.parse(self.ontology_file, format="xml")
                print(f"✅ Ontology loaded successfully: {len(self.graph)} triples")
            except Exception as e:
                print(f"⚠️ Error loading ontology: {e}")
                self._create_minimal_ontology()
        else:
            print(f"⚠️ Ontology file not found: {self.ontology_file}")
            self._create_minimal_ontology()
    
    def _create_minimal_ontology(self):
        """Create a minimal ontology structure if file doesn't exist"""
        # Add basic classes
        self.graph.add((self.SQLTUTOR.SQLQuery, RDF.type, OWL.Class))
        self.graph.add((self.SQLTUTOR.Error, RDF.type, OWL.Class))
        self.graph.add((self.SQLTUTOR.Feedback, RDF.type, OWL.Class))
        self.graph.add((self.SQLTUTOR.Table, RDF.type, OWL.Class))
        self.graph.add((self.SQLTUTOR.Column, RDF.type, OWL.Class))
        
        print("✅ Created minimal ontology structure")
    
    def _extract_knowledge(self):
        """Extract knowledge from the ontology for quick access"""
        self.schema_tables = {}
        self.error_patterns = {}
        self.feedback_messages = {}
        self.sql_concepts = {}
        
        self._extract_schema()
        self._extract_error_patterns()
        self._extract_feedback_messages()
        self._extract_sql_concepts()
    
    def _extract_schema(self):
        """Extract database schema information from ontology"""
        # Extract tables
        query = """
        SELECT ?table ?tableName
        WHERE {
            ?table rdf:type sqltutor:Table .
            ?table sqltutor:tableName ?tableName .
        }
        """
        tables = self.execute_sparql(query)
        
        for table_uri, table_name in tables:
            table_key = str(table_name).lower()
            self.schema_tables[table_key] = {
                'name': str(table_name),
                'columns': {},
                'uri': table_uri
            }
            
            # Extract columns for this table
            column_query = f"""
            SELECT ?column ?columnName ?dataType ?isNullable ?isPrimaryKey
            WHERE {{
                ?column sqltutor:belongsToTable <{table_uri}> .
                ?column sqltutor:columnName ?columnName .
                OPTIONAL {{ ?column sqltutor:hasDataType ?dataType }} .
                OPTIONAL {{ ?column sqltutor:isNullable ?isNullable }} .
                OPTIONAL {{ ?column sqltutor:isPrimaryKey ?isPrimaryKey }} .
            }}
            """
            columns = self.execute_sparql(column_query)
            
            for col_uri, col_name, data_type, is_nullable, is_primary in columns:
                col_key = str(col_name).lower()
                self.schema_tables[table_key]['columns'][col_key] = {
                    'name': str(col_name),
                    'type': self._extract_data_type_label(data_type) if data_type else 'VARCHAR',
                    'nullable': str(is_nullable).lower() == 'true' if is_nullable else True,
                    'primary_key': str(is_primary).lower() == 'true' if is_primary else False,
                    'uri': col_uri
                }
    
    def _extract_data_type_label(self, data_type_uri):
        """Extract human-readable data type label from URI"""
        if not data_type_uri:
            return 'VARCHAR'
        
        query = f"SELECT ?label WHERE {{ <{data_type_uri}> rdfs:label ?label }}"
        result = self.execute_sparql(query)
        return str(result[0][0]) if result else 'VARCHAR'
    
    def _extract_error_patterns(self):
        """Extract error patterns and messages from ontology"""
        query = """
        SELECT ?error ?message ?type ?severity ?explanation
        WHERE {
            ?error rdf:type/rdfs:subClassOf* sqltutor:Error .
            ?error sqltutor:errorMessage ?message .
            OPTIONAL { ?error sqltutor:errorType ?type } .
            OPTIONAL { ?error sqltutor:severity ?severity } .
            OPTIONAL { ?error sqltutor:explanation ?explanation } .
        }
        """
        errors = self.execute_sparql(query)
        
        for error_uri, message, error_type, severity, explanation in errors:
            # Extract error class name from URI
            error_class = str(error_uri).split('#')[-1].replace('_instance', '').replace('_error', '')
            # Convert to snake_case for matching
            error_key = ''.join(['_'+c.lower() if c.isupper() else c for c in error_class]).lstrip('_')
            
            self.error_patterns[error_key] = {
                'message': str(message),
                'type': str(error_type) if error_type else 'SEMANTIC_ERROR',
                'severity': str(severity) if severity else 'MEDIUM',
                'explanation': str(explanation) if explanation else '',
                'uri': error_uri
            }
    
    def _extract_feedback_messages(self):
        """Extract feedback and suggestion messages from ontology"""
        query = """
        SELECT ?suggestion ?message ?type
        WHERE {
            ?suggestion rdf:type/rdfs:subClassOf* sqltutor:Suggestion .
            ?suggestion sqltutor:suggestionMessage ?message .
            OPTIONAL { ?suggestion sqltutor:suggestionType ?type } .
        }
        """
        suggestions = self.execute_sparql(query)
        
        for sugg_uri, message, sugg_type in suggestions:
            sugg_class = str(sugg_uri).split('#')[-1].replace('_instance', '').replace('_suggestion', '')
            # Convert to snake_case
            sugg_key = ''.join(['_'+c.lower() if c.isupper() else c for c in sugg_class]).lstrip('_')
            
            self.feedback_messages[sugg_key] = {
                'message': str(message),
                'type': str(sugg_type) if sugg_type else 'SUGGESTION'
            }
    
    def _extract_sql_concepts(self):
        """Extract SQL concepts and their prerequisites"""
        query = """
        SELECT ?concept ?label ?difficulty ?prerequisite
        WHERE {
            ?concept rdf:type sqltutor:SQLConcept .
            ?concept rdfs:label ?label .
            OPTIONAL { ?concept sqltutor:difficultyLevel ?difficulty } .
            OPTIONAL { ?concept sqltutor:hasPrerequisite ?prerequisite } .
        }
        """
        concepts = self.execute_sparql(query)
        
        for concept_uri, label, difficulty, prerequisite in concepts:
            concept_key = str(concept_uri).split('#')[-1]
            self.sql_concepts[concept_key] = {
                'label': str(label),
                'difficulty': int(difficulty) if difficulty else 1,
                'prerequisite': str(prerequisite).split('#')[-1] if prerequisite else None,
                'uri': concept_uri
            }
    
    def execute_sparql(self, query_str):
        """Execute SPARQL query and return results"""
        try:
            query = prepareQuery(query_str, initNs={"sqltutor": self.SQLTUTOR, "rdf": RDF, "rdfs": RDFS})
            results = self.graph.query(query)
            return [tuple(str(term) if term else None for term in row) for row in results]
        except Exception as e:
            print(f"SPARQL query error: {e}")
            return []
    
    def get_concept_prerequisites(self, concept_name):
        """Get all prerequisites for a concept (transitive closure)"""
        prerequisites = []
        current_concept = concept_name
        
        while current_concept in self.sql_concepts:
            prereq = self.sql_concepts[current_concept].get('prerequisite')
            if prereq and prereq in self.sql_concepts:
                prerequisites.append(prereq)
                current_concept = prereq
            else:
                break
        
        return prerequisites
    
    def suggest_learning_path(self, current_errors):
        """Suggest learning path based on errors encountered"""
        concepts_needed = set()
        
        for error_type in current_errors:
            error_type_lower = error_type.lower()
            # Map error types to concepts
            if 'aggregate' in error_type_lower:
                concepts_needed.add('aggregate_functions_concept')
                concepts_needed.add('group_by_concept')
            elif 'group' in error_type_lower or 'having' in error_type_lower:
                concepts_needed.add('group_by_concept')
                concepts_needed.add('having_clause_concept')
            elif 'join' in error_type_lower:
                concepts_needed.add('join_concept')
            elif 'where' in error_type_lower:
                concepts_needed.add('where_clause_concept')
        
        # Add prerequisites
        all_concepts = set(concepts_needed)
        for concept in concepts_needed:
            all_concepts.update(self.get_concept_prerequisites(concept))
        
        # Return sorted by difficulty
        return sorted(all_concepts, key=lambda c: self.sql_concepts.get(c, {}).get('difficulty', 1))


class SQLTutorEngine:
    """Enhanced core engine for SQL query analysis and feedback generation with ontology integration"""
    
    def __init__(self, ontology_file="sql_tutor_ontology.owl"):
        # Initialize ontology manager
        self.ontology = OntologyManager(ontology_file)
        
        # Use schema from ontology
        self.schema = self._build_schema_from_ontology()
        
        # Initialize sample database
        self._init_sample_database()
        
        # Knowledge base representing ontological rules
        self.error_patterns = self._initialize_error_patterns()
        self.aggregate_functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']
        self.sql_keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'ON', 'AND', 'OR', 'NOT', 'AS']
        
    def _build_schema_from_ontology(self):
        """Build database schema from ontology"""
        schema = {}
        
        for table_key, table_info in self.ontology.schema_tables.items():
            schema[table_key] = {
                'columns': {},
                'foreign_keys': {}
            }
            
            for col_key, col_info in table_info['columns'].items():
                schema[table_key]['columns'][col_key] = {
                    'type': col_info['type'],
                    'nullable': col_info['nullable'],
                    'primary_key': col_info['primary_key']
                }
                
                # Extract foreign keys from ontology
                if 'manager_id' in col_key and table_key == 'employees':
                    schema[table_key]['foreign_keys']['manager_id'] = 'employees(emp_id)'
        
        return schema
    
    def _init_sample_database(self):
        """Initialize a sample SQLite database with realistic data"""
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create tables based on ontology schema
        self.cursor.execute('''
            CREATE TABLE employees (
                emp_id INTEGER PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                department VARCHAR(50),
                salary DECIMAL(10,2),
                hire_date DATE,
                manager_id INTEGER
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE departments (
                dept_id INTEGER PRIMARY KEY,
                dept_name VARCHAR(50) NOT NULL,
                location VARCHAR(100),
                budget DECIMAL(12,2)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE projects (
                project_id INTEGER PRIMARY KEY,
                project_name VARCHAR(100) NOT NULL,
                department VARCHAR(50),
                start_date DATE,
                end_date DATE,
                budget DECIMAL(12,2)
            )
        ''')
        
        # Insert sample data
        self._insert_sample_data()
        
    def _insert_sample_data(self):
        """Insert realistic sample data"""
        # Employees data
        employees_data = [
            (1, 'John', 'Smith', 'Engineering', 75000.00, '2020-01-15', None),
            (2, 'Sarah', 'Johnson', 'Engineering', 80000.00, '2019-03-20', 1),
            (3, 'Michael', 'Brown', 'Sales', 65000.00, '2021-06-10', None),
            (4, 'Emily', 'Davis', 'Sales', 60000.00, '2022-02-01', 3),
            (5, 'David', 'Wilson', 'HR', 55000.00, '2020-11-30', None),
            (6, 'Lisa', 'Miller', 'Engineering', 90000.00, '2018-08-12', 1),
            (7, 'Robert', 'Taylor', 'Marketing', 70000.00, '2021-09-05', None)
        ]
        
        departments_data = [
            (1, 'Engineering', 'New York', 1000000.00),
            (2, 'Sales', 'Chicago', 800000.00),
            (3, 'HR', 'Boston', 500000.00),
            (4, 'Marketing', 'San Francisco', 600000.00)
        ]
        
        projects_data = [
            (1, 'Website Redesign', 'Engineering', '2023-01-01', '2023-06-30', 150000.00),
            (2, 'Sales Portal', 'Sales', '2023-02-15', '2023-08-31', 100000.00),
            (3, 'HR System', 'HR', '2023-03-01', '2023-12-31', 200000.00)
        ]
        
        self.cursor.executemany('INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?)', employees_data)
        self.cursor.executemany('INSERT INTO departments VALUES (?, ?, ?, ?)', departments_data)
        self.cursor.executemany('INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)', projects_data)
        self.conn.commit()
    
    def _initialize_error_patterns(self):
        """Initialize comprehensive error detection patterns using ontology"""
        patterns = {
            'missing_select': {
                'pattern': r'^\s*(?!SELECT)',
                'check_function': None,
                'type': 'SYNTAX_ERROR',
                'severity': 'HIGH'
            },
            'missing_from': {
                'pattern': None,  # Will be checked programmatically
                'check_function': 'check_missing_from',
                'type': 'SYNTAX_ERROR',
                'severity': 'HIGH'
            },
            'aggregate_in_where': {
                'pattern': None,
                'check_function': 'check_aggregate_in_where',
                'type': 'SEMANTIC_ERROR',
                'severity': 'HIGH'
            },
            'missing_group_by': {
                'pattern': None,
                'check_function': 'check_missing_group_by',
                'type': 'SEMANTIC_ERROR',
                'severity': 'HIGH'
            },
            'having_without_group': {
                'pattern': None,
                'check_function': 'check_having_without_group',
                'type': 'SEMANTIC_ERROR',
                'severity': 'MEDIUM'
            },
            'ambiguous_column': {
                'pattern': None,
                'check_function': 'check_ambiguous_columns',
                'type': 'SEMANTIC_ERROR',
                'severity': 'MEDIUM'
            },
            'group_by_column_not_in_select': {
                'pattern': None,
                'check_function': 'check_group_by_column_not_in_select',
                'type': 'SEMANTIC_ERROR',
                'severity': 'HIGH'
            },
            'missing_aggregate_with_group_by': {
                'pattern': None,
                'check_function': 'check_missing_aggregate_with_group_by',
                'type': 'SEMANTIC_ERROR',
                'severity': 'HIGH'
            }
        }
        
        # Enhance patterns with ontology data
        for pattern_key, pattern in patterns.items():
            if pattern_key in self.ontology.error_patterns:
                ontology_error = self.ontology.error_patterns[pattern_key]
                pattern['message'] = ontology_error['message']
                pattern['explanation'] = ontology_error.get('explanation', '')
                pattern['type'] = ontology_error.get('type', pattern['type'])
                pattern['severity'] = ontology_error.get('severity', pattern['severity'])
            else:
                # Fallback messages
                pattern['message'] = f"Error detected: {pattern_key.replace('_', ' ').title()}"
                pattern['explanation'] = "Refer to SQL documentation for proper usage."
        
        return patterns
    
    def analyze_query(self, query_text):
        """Enhanced analysis pipeline with ontology-based reasoning"""
        feedback = {
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'learning_path': [],
            'correctness': 'UNKNOWN',
            'execution_result': None
        }
        
        if not query_text.strip():
            feedback['errors'].append({
                'message': 'Please enter a SQL query.',
                'type': 'EMPTY_INPUT',
                'severity': 'LOW'
            })
            return feedback
        
        # Parse the query
        try:
            parsed = sqlparse.parse(query_text)[0]
        except Exception as e:
            feedback['errors'].append({
                'message': f'Failed to parse query: {str(e)}',
                'type': 'PARSE_ERROR',
                'severity': 'HIGH'
            })
            return feedback
        
        # Syntactic validation
        syntax_errors = self._check_syntax(query_text, parsed)
        feedback['errors'].extend(syntax_errors)
        
        # Semantic validation (ontology-based reasoning)
        semantic_errors = self._check_semantics(query_text, parsed)
        feedback['errors'].extend(semantic_errors)
        
        # Check against schema (domain constraints)
        schema_errors = self._check_schema_constraints(query_text, parsed)
        feedback['errors'].extend(schema_errors)
        
        # Try to execute the query if no critical errors
        execution_feedback = self._try_execute_query(query_text, parsed)
        if execution_feedback:
            if 'error' in execution_feedback:
                feedback['errors'].append(execution_feedback['error'])
            else:
                feedback['execution_result'] = execution_feedback.get('result')
        
        # Generate ontology-based suggestions
        suggestions = self._generate_ontology_suggestions(query_text, parsed, feedback['errors'])
        feedback['suggestions'].extend(suggestions)
        
        # Generate learning path based on errors
        error_types = [error.get('type', '') for error in feedback['errors']]
        feedback['learning_path'] = self.ontology.suggest_learning_path(error_types)
        
        # Determine overall correctness
        if not feedback['errors']:
            feedback['correctness'] = 'CORRECT'
            feedback['suggestions'].insert(0, {
                'message': '✓ Query is syntactically and semantically correct!',
                'type': 'SUCCESS',
                'severity': 'LOW',
                'source': 'ontology'
            })
        elif any(e.get('severity') == 'HIGH' for e in feedback['errors']):
            feedback['correctness'] = 'INCORRECT'
        else:
            feedback['correctness'] = 'PARTIAL'
        
        return feedback
    
    def _check_syntax(self, query_text, parsed):
        """Enhanced syntax checking using ontology patterns"""
        errors = []
        query_upper = query_text.upper().strip()
        
        # Check if query starts with SELECT
        if not query_upper.startswith('SELECT'):
            pattern = self.error_patterns.get('missing_select', {})
            errors.append({
                'message': pattern.get('message', 'Query must start with SELECT keyword.'),
                'type': pattern.get('type', 'SYNTAX_ERROR'),
                'severity': pattern.get('severity', 'HIGH'),
                'explanation': pattern.get('explanation', ''),
                'source': 'ontology'
            })
        
        # Additional syntax checks
        clause_order_error = self._check_clause_order(query_text)
        if clause_order_error:
            # Use ontology message for clause order if available
            if 'clause_order' in self.ontology.error_patterns:
                ontology_error = self.ontology.error_patterns['clause_order']
                clause_order_error.update({
                    'message': ontology_error['message'],
                    'explanation': ontology_error.get('explanation', ''),
                    'source': 'ontology'
                })
            errors.append(clause_order_error)
        
        return errors
    
    def _check_semantics(self, query_text, parsed):
        """Enhanced semantic checking using ontology patterns"""
        errors = []
        
        # Check function-based patterns from ontology
        for pattern_key, pattern in self.error_patterns.items():
            if pattern.get('check_function'):
                check_method = getattr(self, pattern['check_function'], None)
                if check_method and check_method(parsed, query_text):
                    errors.append({
                        'message': pattern['message'],
                        'type': pattern['type'],
                        'severity': pattern['severity'],
                        'explanation': pattern.get('explanation', ''),
                        'source': 'ontology'
                    })
        
        return errors
    
    def _generate_ontology_suggestions(self, query_text, parsed, errors):
        """Generate suggestions using ontology knowledge"""
        suggestions = []
        query_upper = query_text.upper()
        
        # Use ontology feedback messages
        for sugg_key, sugg_info in self.ontology.feedback_messages.items():
            # Context-based suggestion triggering
            if ('ORDER BY' not in query_upper and 
                'order_by' in sugg_key.lower() and
                'GROUP BY' not in query_upper):
                suggestions.append({
                    'message': sugg_info['message'],
                    'type': sugg_info['type'],
                    'severity': 'LOW',
                    'source': 'ontology'
                })
            elif ('*' in query_text and 
                'select_star' in sugg_key.lower() and
                'COUNT(*)' not in query_upper):
                suggestions.append({
                    'message': sugg_info['message'],
                    'type': sugg_info['type'],
                    'severity': 'LOW',
                    'source': 'ontology'
                })
            elif ('employees' in query_upper and 
                'departments' in query_upper and 
                'join' in sugg_key.lower() and
                'JOIN' not in query_upper):
                suggestions.append({
                    'message': sugg_info['message'],
                    'type': sugg_info['type'],
                    'severity': 'MEDIUM',
                    'source': 'ontology'
                })
            elif ('GROUP BY' in query_upper and
                'group_by_aggregate' in sugg_key.lower()):
                # Check if we have GROUP BY but might need aggregate functions
                select_clause = self._extract_select_clause(parsed).upper()
                has_aggregate = any(f"{func}(" in select_clause or f"{func} (" in select_clause 
                                for func in self.aggregate_functions)
                if not has_aggregate:
                    suggestions.append({
                        'message': sugg_info['message'],
                        'type': sugg_info['type'],
                        'severity': 'MEDIUM',
                        'source': 'ontology'
                    })
            elif ('GROUP BY' in query_upper and
                'group_by_select' in sugg_key.lower()):
                # Check if GROUP BY columns might not be in SELECT
                group_by_columns = self._extract_group_by_columns(parsed)
                select_clause = self._extract_select_clause(parsed)
                select_columns = self._extract_all_columns_from_select(select_clause)
                
                missing_in_select = any(group_col.upper() not in [col.upper() for col in select_columns] 
                                    for group_col in group_by_columns)
                
                if missing_in_select:
                    suggestions.append({
                        'message': sugg_info['message'],
                        'type': sugg_info['type'],
                        'severity': 'MEDIUM',
                        'source': 'ontology'
                    })
        
        return suggestions

    def _check_clause_order(self, query_text):
        """Check if SQL clauses are in proper order"""
        query_upper = query_text.upper()
        clauses = []
        
        for clause in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY']:
            if clause in query_upper:
                clauses.append(clause)
        
        # Expected order
        expected_order = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY']
        filtered_expected = [c for c in expected_order if c in clauses]
        
        if clauses != filtered_expected:
            return {
                'message': f'SQL clauses should follow this order: SELECT -> FROM -> WHERE -> GROUP BY -> HAVING -> ORDER BY. Found: {" -> ".join(clauses)}',
                'type': 'SYNTAX_ERROR',
                'severity': 'MEDIUM'
            }
        return None
    
    def _has_aggregate_in_where(self, parsed):
        """Check if WHERE clause contains aggregate functions"""
        query_str = str(parsed).upper()
        
        # Find WHERE clause
        where_start = query_str.find('WHERE')
        if where_start == -1:
            return False
        
        # Find end of WHERE clause
        where_end = len(query_str)
        for keyword in ['GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT']:
            pos = query_str.find(keyword, where_start)
            if pos != -1:
                where_end = min(where_end, pos)
        
        where_clause = query_str[where_start:where_end]
        
        # Check for aggregate functions
        for func in self.aggregate_functions:
            if func + '(' in where_clause:
                return True
        
        return False
    
    def _needs_group_by(self, parsed, query_text):
        """Check if query needs GROUP BY clause (has both aggregate and non-aggregate columns)"""
        query_upper = query_text.upper()
        
        # If already has GROUP BY, no error
        if 'GROUP BY' in query_upper:
            return False
        
        # Extract SELECT clause
        select_clause = self._extract_select_clause(parsed)
        if not select_clause:
            return False
        
        # Check for aggregate functions in SELECT clause
        has_aggregate = any(func in select_clause for func in self.aggregate_functions)
        
        if has_aggregate:
            # Extract all column references from SELECT clause
            all_columns = self._extract_columns_from_select(select_clause)
            
            # Filter out columns that are inside aggregate functions
            non_aggregate_columns = []
            for col in all_columns:
                # Check if this column appears inside any aggregate function
                col_in_aggregate = False
                for func in self.aggregate_functions:
                    # Look for patterns like "FUNC( ... col ... )"
                    pattern = rf"{func}\s*\([^)]*{re.escape(col)}[^)]*\)"
                    if re.search(pattern, select_clause, re.IGNORECASE):
                        col_in_aggregate = True
                        break
                
                if not col_in_aggregate:
                    non_aggregate_columns.append(col)
            
            # If we have both aggregate functions AND non-aggregate columns, need GROUP BY
            if non_aggregate_columns:
                return True
        
        return False
    
    def check_missing_group_by(self, parsed, query_text):
        """Check if query needs GROUP BY clause (has both aggregate and non-aggregate columns)"""
        query_upper = query_text.upper()
        
        print(f"DEBUG check_missing_group_by: Checking query: {query_text}")
        
        # If already has GROUP BY, no error
        if 'GROUP BY' in query_upper:
            print("DEBUG: Has GROUP BY, returning False")
            return False
        
        # Extract SELECT clause
        select_clause = self._extract_select_clause(parsed)
        print(f"DEBUG: Raw SELECT clause: {select_clause}")
        
        if not select_clause:
            print("DEBUG: No SELECT clause, returning False")
            return False
        
        # Check for aggregate functions in SELECT clause
        has_aggregate = any(func in select_clause.upper() for func in self.aggregate_functions)
        print(f"DEBUG: Has aggregate: {has_aggregate}")
        
        # If no aggregates, no GROUP BY needed
        if not has_aggregate:
            print("DEBUG: No aggregates, returning False")
            return False
        
        # Extract all column references from SELECT clause
        all_columns = self._extract_columns_from_select(select_clause)
        print(f"DEBUG: All extracted columns: {all_columns}")
        
        # If we have aggregates but NO other columns, then no GROUP BY needed
        # This is the key: pure aggregate queries are valid without GROUP BY
        if not all_columns:
            print("DEBUG: No non-aggregate columns found, returning False")
            return False
        
        # If we get here and have columns, check if they're truly non-aggregate
        # For now, we'll assume any remaining columns need GROUP BY
        print("DEBUG: Has non-aggregate columns, returning True")
        return True
        # Simple check: if SELECT contains only aggregates (no commas or only aggregates with commas), then no GROUP BY needed
        # Remove all aggregate function calls
        temp_clause = select_upper
        for func in self.aggregate_functions:
            temp_clause = re.sub(rf'{func}\s*\([^)]*\)', '', temp_clause, flags=re.IGNORECASE)
        
        # Remove common SQL elements
        temp_clause = re.sub(r'\bAS\s+\w+', '', temp_clause)  # Remove aliases
        temp_clause = re.sub(r'[*]', '', temp_clause)  # Remove asterisks
        
        # Clean up: remove extra spaces and commas
        temp_clause = re.sub(r'\s+', ' ', temp_clause).strip()
        temp_clause = temp_clause.replace(',', ' ').strip()
        
        # If nothing left after removing aggregates and cleaning, then it's pure aggregate query
        if not temp_clause or temp_clause.isspace():
            return False
        
        # If we get here, there are non-aggregate elements that need GROUP BY
        return True

    def check_missing_aggregate_with_group_by(self, parsed, query_text):
        """Check if GROUP BY is used without aggregate functions"""
        query_upper = query_text.upper()
        
        # Check if GROUP BY is present
        if 'GROUP BY' in query_upper:
            # Extract SELECT clause in uppercase for consistent checking
            select_clause = self._extract_select_clause(parsed).upper()
            
            # Check if any aggregate functions are in SELECT clause
            has_aggregate = False
            for func in self.aggregate_functions:
                # Look for patterns like "FUNC(" or "FUNC ("
                if f"{func}(" in select_clause or f"{func} (" in select_clause:
                    has_aggregate = True
                    break
            
            # If GROUP BY is present but no aggregates, it's an error
            if not has_aggregate:
                return True
        
        return False
        
    def check_group_by_column_not_in_select(self, parsed, query_text):
        """Check if GROUP BY uses columns not in SELECT clause"""
        query_upper = query_text.upper()
        
        # Check if GROUP BY is present
        if 'GROUP BY' in query_upper:
            # Extract GROUP BY columns
            group_by_columns = self._extract_group_by_columns(parsed)
            
            # Extract SELECT columns
            select_clause = self._extract_select_clause(parsed)
            select_columns = self._extract_all_columns_from_select(select_clause)
            
            # Check if any GROUP BY column is not in SELECT
            for group_col in group_by_columns:
                if group_col.upper() not in [col.upper() for col in select_columns]:
                    return True
        
        return False

    def _extract_group_by_columns(self, parsed):
        """Extract column names from GROUP BY clause"""
        query_str = str(parsed).upper()
        group_by_start = query_str.find('GROUP BY')
        if group_by_start == -1:
            return []
        
        # Find end of GROUP BY clause
        group_by_end = len(query_str)
        for keyword in ['HAVING', 'ORDER BY', 'LIMIT']:
            pos = query_str.find(keyword, group_by_start)
            if pos != -1:
                group_by_end = min(group_by_end, pos)
        
        group_by_clause = query_str[group_by_start+8:group_by_end].strip()
        
        # Extract column names (simple approach - split by commas)
        columns = []
        for part in group_by_clause.split(','):
            column = part.strip().split()[0]  # Take first word (column name)
            if column and column not in self.sql_keywords:
                columns.append(column)
        
        return columns

    def _extract_all_columns_from_select(self, select_clause):
        """Extract ALL column names from SELECT clause, including those in aggregates"""
        # Extract all column-like words, then filter
        columns = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', select_clause)
        
        # Filter out SQL keywords and numbers
        columns = [c for c in columns if c.upper() not in self.sql_keywords + ['AS'] and not c.isdigit()]
        
        return columns
    
    def check_missing_from(self, parsed, query_text):
        """Check if FROM clause is missing"""
        query_upper = query_text.upper()
        return 'SELECT' in query_upper and 'FROM' not in query_upper
    
    def check_aggregate_in_where(self, parsed, query_text):
        return self._has_aggregate_in_where(parsed)
    
    def check_missing_group_by(self, parsed, query_text):
        return self._needs_group_by(parsed, query_text)
    
    def check_having_without_group(self, parsed, query_text):
        query_upper = query_text.upper()
        return 'HAVING' in query_upper and 'GROUP BY' not in query_upper
    
    def check_ambiguous_columns(self, parsed, query_text):
        ambiguous_cols = self._find_ambiguous_columns(parsed)
        return len(ambiguous_cols) > 0
    
    def _find_ambiguous_columns(self, parsed):
        """Find ambiguous column references in multi-table queries"""
        tables = self._extract_table_names(parsed)
        if len(tables) < 2:
            return []
        
        # Get all columns from all tables
        all_columns = {}
        for table in tables:
            if table.lower() in self.schema:
                all_columns[table] = set(self.schema[table.lower()]['columns'].keys())
        
        # Find columns that appear in multiple tables
        column_occurrences = {}
        for table, columns in all_columns.items():
            for col in columns:
                if col not in column_occurrences:
                    column_occurrences[col] = []
                column_occurrences[col].append(table)
        
        ambiguous_cols = [col for col, tables in column_occurrences.items() if len(tables) > 1]
        
        # Check if these columns are used without table qualification
        query_str = str(parsed)
        used_ambiguous = []
        for col in ambiguous_cols:
            # Look for column usage without table prefix
            pattern = r'\b' + re.escape(col) + r'\b'
            matches = re.findall(pattern, query_str, re.IGNORECASE)
            if matches:
                # Check if it's qualified with table name
                for match in matches:
                    # Look backwards for table qualification
                    pos = query_str.lower().find(match.lower())
                    if pos > 0:
                        preceding = query_str[max(0, pos-20):pos].strip()
                        if not any(table.lower() in preceding for table in tables):
                            used_ambiguous.append(col)
                            break
        
        return list(set(used_ambiguous))
    
    def _extract_select_clause(self, parsed):
        """Extract SELECT clause content"""
        query_str = str(parsed).upper()
        select_start = query_str.find('SELECT')
        if select_start == -1:
            return ''
        
        from_start = query_str.find('FROM', select_start)
        if from_start == -1:
            return query_str[select_start:]
        
        return query_str[select_start:from_start]
    
    def _extract_columns_from_select(self, select_clause):
        """Extract column names from SELECT clause, excluding those in aggregate functions and aliases"""
        # Convert to uppercase for consistent processing
        temp_clause = select_clause.upper()
        
        # First, remove all aggregate functions and their content
        for func in self.aggregate_functions:
            # Remove patterns like FUNC(...), FUNC (...), FUNC ( ... ), etc.
            pattern = rf"{func}\s*\(\s*[^)]*\s*\)"
            temp_clause = re.sub(pattern, '', temp_clause)
        
        # Remove aliases (both explicit "AS alias" and implicit "expression alias")
        # Remove explicit aliases: AS alias_name
        temp_clause = re.sub(r'\bAS\s+[a-zA-Z_][a-zA-Z0-9_]*', '', temp_clause)
        
        # Remove implicit aliases: expression alias_name (without AS)
        # This is more complex - we need to identify patterns where a word follows an expression
        # Simple approach: remove any standalone words that aren't SQL keywords
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', temp_clause)
        
        # Filter out SQL keywords, numbers, and common function names
        excluded_keywords = self.sql_keywords + ['FROM', 'WHERE', 'GROUP', 'HAVING', 'ORDER', 'BY', 'JOIN', 'ON', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'AS']
        filtered_words = [w for w in words if w.upper() not in excluded_keywords and not w.isdigit()]
        
        # Now, from the remaining words, we need to identify which are actual column references
        # For simplicity, we'll assume any remaining word that matches our column pattern is a column
        # But we need to be careful about table aliases and other non-column identifiers
        
        return filtered_words
    
    def _extract_table_names(self, parsed):
        """Extract all table names from FROM and JOIN clauses"""
        tables = []
        query_str = str(parsed).upper()
        
        # Find FROM clause tables
        from_start = query_str.find('FROM')
        if from_start != -1:
            # Find end of FROM clause
            from_end = len(query_str)
            for keyword in ['WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'JOIN']:
                pos = query_str.find(keyword, from_start)
                if pos != -1:
                    from_end = min(from_end, pos)
            
            from_clause = query_str[from_start+4:from_end].strip()
            # Extract table names (simple approach)
            tables.extend([tbl.strip().split()[0] for tbl in from_clause.split(',')])
        
        # Find JOIN clause tables
        join_pos = query_str.find('JOIN')
        while join_pos != -1:
            join_end = query_str.find('ON', join_pos)
            if join_end == -1:
                break
            join_table = query_str[join_pos+4:join_end].strip().split()[0]
            tables.append(join_table)
            join_pos = query_str.find('JOIN', join_pos + 1)
        
        return [tbl for tbl in tables if tbl and tbl.upper() not in ['INNER', 'LEFT', 'RIGHT', 'FULL']]
    
    def _check_schema_constraints(self, query_text, parsed):
        """Enhanced schema validation using ontology schema"""
        errors = []
        
        # Extract table names
        table_names = self._extract_table_names(parsed)
        if not table_names:
            return errors  # No tables to check (might be a subquery or other valid case)
        
        # Check table existence using ontology schema
        for table_name in table_names:
            if table_name.lower() not in self.schema:
                # Try to suggest correct table name
                suggestions = []
                for actual_table in self.schema.keys():
                    if table_name.lower() in actual_table or actual_table in table_name.lower():
                        suggestions.append(actual_table)
                
                error_msg = f"Table '{table_name}' does not exist in the database schema."
                if suggestions:
                    error_msg += f" Did you mean: {', '.join(suggestions)}?"
                
                errors.append({
                    'message': error_msg,
                    'type': 'SCHEMA_ERROR',
                    'severity': 'HIGH',
                    'available_tables': list(self.schema.keys())
                })
        
        return errors
    
    def _try_execute_query(self, query_text, parsed):
        """Try to execute the query and return results or errors"""
        try:
            # Basic safety check - prevent destructive operations
            query_upper = query_text.upper().strip()
            destructive_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
            if any(keyword in query_upper for keyword in destructive_keywords):
                return {
                    'error': {
                        'message': 'This tutoring system only supports SELECT queries for learning purposes.',
                        'type': 'SECURITY_ERROR',
                        'severity': 'HIGH'
                    }
                }
            
            # Execute the query
            self.cursor.execute(query_text)
            results = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            
            return {
                'result': {
                    'columns': columns,
                    'data': results[:10],  # Limit to first 10 rows for display
                    'row_count': len(results)
                }
            }
            
        except sqlite3.Error as e:
            return {
                'error': {
                    'message': f'Execution error: {str(e)}',
                    'type': 'EXECUTION_ERROR',
                    'severity': 'HIGH',
                    'explanation': 'The query failed to execute against the sample database.'
                }
            }


class SQLTutorGUI:
    """Enhanced user interface for SQL Intelligent Tutoring System with ontology integration"""
    
    def __init__(self, ontology_file="sql_tutor_ontology.owl"):
        self.engine = SQLTutorEngine(ontology_file)
        self.window = tk.Tk()
        self.window.title("SQL Intelligent Tutoring System v2.0 with Ontology")
        self.window.geometry("1200x800")
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        self._create_widgets()
        self._show_welcome_message()
        
    def _create_widgets(self):
        """Create all GUI components"""
        
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🧠 SQL Intelligent Tutoring System v2.0 with Ontology", 
                                font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, pady=10)
        
        # Schema display frame
        schema_frame = ttk.LabelFrame(main_frame, text="📊 Database Schema (from Ontology)", padding="10")
        schema_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        schema_frame.columnconfigure(0, weight=1)
        
        # Create a scrolled text widget for schema
        self.schema_display = scrolledtext.ScrolledText(schema_frame, height=6, width=80,
                                                       font=('Courier', 9), wrap=tk.WORD)
        self.schema_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Make schema display read-only
        self.schema_display.config(state=tk.NORMAL)
        schema_text = self._get_schema_display()
        self.schema_display.insert('1.0', schema_text)
        self.schema_display.config(state=tk.DISABLED)
        
        # Query input frame
        query_frame = ttk.LabelFrame(main_frame, text="✏️ Enter Your SQL Query", padding="10")
        query_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        query_frame.columnconfigure(0, weight=1)
        
        self.query_editor = scrolledtext.ScrolledText(query_frame, height=6, width=80,
                                                      font=('Courier', 11),
                                                      wrap=tk.WORD)
        self.query_editor.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Button frame
        button_frame = ttk.Frame(query_frame)
        button_frame.grid(row=1, column=0, pady=5)
        
        self.submit_btn = ttk.Button(button_frame, text="🔍 Analyze Query", 
                                     command=self.submit_query)
        self.submit_btn.grid(row=0, column=0, padx=5)
        
        clear_btn = ttk.Button(button_frame, text="🗑️ Clear", 
                              command=self.clear_query)
        clear_btn.grid(row=0, column=1, padx=5)
        
        example_btn = ttk.Button(button_frame, text="💡 Load Example", 
                                command=self.load_example)
        example_btn.grid(row=0, column=2, padx=5)
        
        # Create notebook for different feedback tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Feedback tab
        feedback_frame = ttk.Frame(notebook, padding="10")
        notebook.add(feedback_frame, text="📋 Analysis & Feedback")
        feedback_frame.columnconfigure(0, weight=1)
        feedback_frame.rowconfigure(0, weight=1)
        
        self.feedback_display = scrolledtext.ScrolledText(feedback_frame, height=12, width=80,
                                                          font=('Arial', 10),
                                                          wrap=tk.WORD)
        self.feedback_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Results tab
        results_frame = ttk.Frame(notebook, padding="10")
        notebook.add(results_frame, text="📊 Query Results")
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        self.results_display = scrolledtext.ScrolledText(results_frame, height=12, width=80,
                                                         font=('Courier', 9),
                                                         wrap=tk.WORD)
        self.results_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Learning Path tab
        learning_frame = ttk.Frame(notebook, padding="10")
        notebook.add(learning_frame, text="🎓 Learning Path")
        learning_frame.columnconfigure(0, weight=1)
        learning_frame.rowconfigure(0, weight=1)
        
        self.learning_display = scrolledtext.ScrolledText(learning_frame, height=12, width=80,
                                                          font=('Arial', 10),
                                                          wrap=tk.WORD)
        self.learning_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for colored output
        for widget in [self.feedback_display, self.results_display, self.learning_display]:
            widget.tag_config('error', foreground='red', font=('Arial', 10, 'bold'))
            widget.tag_config('warning', foreground='orange')
            widget.tag_config('success', foreground='green', font=('Arial', 10, 'bold'))
            widget.tag_config('suggestion', foreground='blue')
            widget.tag_config('header', font=('Arial', 11, 'bold'))
            widget.tag_config('sql', font=('Courier', 10))
            widget.tag_config('ontology', foreground='purple')
        
    def _get_schema_display(self):
        """Generate formatted schema display from ontology"""
        schema_text = "📚 Database Schema (Loaded from Ontology):\n\n"
        
        for table_name, table_info in self.engine.ontology.schema_tables.items():
            schema_text += f"📋 {table_info['name'].upper()}:\n"
            for col_name, col_info in table_info['columns'].items():
                pk_indicator = " 🔑" if col_info.get('primary_key') else ""
                nullable_indicator = "" if col_info.get('nullable', True) else " NOT NULL"
                schema_text += f"   • {col_info['name']}: {col_info['type']}{nullable_indicator}{pk_indicator}\n"
            schema_text += "\n"
        
        schema_text += "💡 Ontology Features:\n"
        schema_text += f"  • {len(self.engine.ontology.error_patterns)} error patterns\n"
        schema_text += f"  • {len(self.engine.ontology.feedback_messages)} feedback messages\n"
        schema_text += f"  • {len(self.engine.ontology.sql_concepts)} SQL concepts\n"
        schema_text += f"  • {len(self.engine.ontology.graph)} semantic triples\n"
        
        return schema_text
    
    def _show_welcome_message(self):
        """Display welcome message with instructions"""
        welcome = """🎓 Welcome to SQL Intelligent Tutoring System v2.0 with Ontology!

This enhanced system uses semantic web technologies to provide intelligent feedback, 
personalized learning paths, and comprehensive error analysis based on SQL knowledge ontology.

📚 HOW TO USE:
1. Review the database schema shown above (loaded from ontology)
2. Write your SQL query in the editor
3. Click 'Analyze Query' to receive ontology-based feedback
4. View results in different tabs:
   - Analysis & Feedback: Errors and suggestions
   - Query Results: Execution results
   - Learning Path: Personalized learning recommendations

💡 ONTOLOGY FEATURES:
• Semantic error detection using knowledge graphs
• Personalized learning path recommendations
• Concept prerequisite tracking
• Intelligent feedback generation

🚀 Click 'Load Example' to see a sample query. Good luck learning SQL!
"""
        self.feedback_display.insert('1.0', welcome)
    
    def submit_query(self):
        """Handle query submission and display feedback"""
        query = self.query_editor.get('1.0', tk.END).strip()
        
        if not query:
            messagebox.showwarning("Empty Query", "Please enter a SQL query first.")
            return
        
        # Clear previous results
        self.feedback_display.delete('1.0', tk.END)
        self.results_display.delete('1.0', tk.END)
        self.learning_display.delete('1.0', tk.END)
        
        # Show analyzing message
        self.feedback_display.insert('1.0', "🔄 Analyzing your query using ontology...\n\n")
        self.feedback_display.update()
        
        # Analyze query using the ontology-enhanced engine
        feedback = self.engine.analyze_query(query)
        
        # Display feedback and results
        self.display_feedback(feedback)
        self.display_results(feedback)
        self.display_learning_path(feedback)
    
    def display_feedback(self, feedback):
        """Display analysis feedback with ontology-based formatting"""
        self.feedback_display.delete('1.0', tk.END)
        
        # Header
        self.feedback_display.insert(tk.END, "=== ONTOLOGY-BASED QUERY ANALYSIS ===\n\n", 'header')
        
        # Display errors
        if feedback['errors']:
            self.feedback_display.insert(tk.END, "❌ ERRORS FOUND:\n", 'error')
            for i, error in enumerate(feedback['errors'], 1):
                tag = 'ontology' if error.get('source') == 'ontology' else 'error'
                self.feedback_display.insert(tk.END, f"\n{i}. {error['message']}\n", tag)
                if 'explanation' in error and error['explanation']:
                    self.feedback_display.insert(tk.END, f"   💡 Explanation: {error['explanation']}\n", 'suggestion')
                if error.get('source') == 'ontology':
                    self.feedback_display.insert(tk.END, "   📚 Source: Ontology Knowledge Base\n", 'ontology')
        else:
            self.feedback_display.insert(tk.END, "✅ No errors found!\n", 'success')
        
        # Display suggestions
        if feedback['suggestions']:
            self.feedback_display.insert(tk.END, "\n\n💡 SUGGESTIONS:\n", 'suggestion')
            for i, suggestion in enumerate(feedback['suggestions'], 1):
                tag = 'success' if suggestion.get('type') == 'SUCCESS' else 'suggestion'
                if suggestion.get('source') == 'ontology':
                    tag = 'ontology'
                self.feedback_display.insert(tk.END, f"\n{i}. {suggestion['message']}\n", tag)
                if suggestion.get('source') == 'ontology':
                    self.feedback_display.insert(tk.END, "   📚 Source: Ontology Knowledge Base\n", 'ontology')
        
        # Overall assessment
        self.feedback_display.insert(tk.END, "\n\n" + "="*50 + "\n", 'header')
        if feedback['correctness'] == 'CORRECT':
            self.feedback_display.insert(tk.END, "✅ STATUS: Query is correct and executable!\n", 'success')
            self.feedback_display.insert(tk.END, "Great job! Your query follows SQL syntax and semantic rules.\n")
        elif feedback['correctness'] == 'INCORRECT':
            self.feedback_display.insert(tk.END, "❌ STATUS: Query has critical errors\n", 'error')
            self.feedback_display.insert(tk.END, "Please review and fix the errors listed above.\n")
        else:
            self.feedback_display.insert(tk.END, "⚠️ STATUS: Query needs improvement\n", 'warning')
            self.feedback_display.insert(tk.END, "Review the suggestions to enhance your query.\n")
    
    def display_results(self, feedback):
        """Display query execution results"""
        self.results_display.delete('1.0', tk.END)
        self.results_display.insert(tk.END, "=== QUERY EXECUTION RESULTS ===\n\n", 'header')
        
        if feedback.get('execution_result'):
            result = feedback['execution_result']
            
            # Display columns
            columns = " | ".join(result['columns'])
            self.results_display.insert(tk.END, f"Columns: {columns}\n\n", 'sql')
            
            # Display data
            self.results_display.insert(tk.END, "Data:\n", 'header')
            for row in result['data']:
                row_str = " | ".join(str(cell) for cell in row)
                self.results_display.insert(tk.END, f"{row_str}\n", 'sql')
            
            # Display row count
            self.results_display.insert(tk.END, f"\nTotal rows: {result['row_count']}\n", 'header')
            if result['row_count'] > 10:
                self.results_display.insert(tk.END, "(Showing first 10 rows)\n", 'suggestion')
                
        else:
            self.results_display.insert(tk.END, "Query was not executed due to errors.\n", 'error')
            self.results_display.insert(tk.END, "Fix the errors in the Analysis tab and try again.\n", 'suggestion')
    
    def display_learning_path(self, feedback):
        """Display personalized learning path based on ontology"""
        self.learning_display.delete('1.0', tk.END)
        self.learning_display.insert(tk.END, "=== PERSONALIZED LEARNING PATH ===\n\n", 'header')
        
        if feedback.get('learning_path'):
            self.learning_display.insert(tk.END, "🎯 Based on your errors, we recommend studying:\n\n", 'header')
            
            for i, concept_key in enumerate(feedback['learning_path'], 1):
                concept = self.engine.ontology.sql_concepts.get(concept_key, {})
                concept_name = concept.get('label', concept_key)
                difficulty = concept.get('difficulty', 1)
                
                difficulty_stars = "★" * difficulty
                self.learning_display.insert(tk.END, f"{i}. {concept_name} {difficulty_stars}\n")
                
                # Show prerequisites if any
                prereqs = self.engine.ontology.get_concept_prerequisites(concept_key)
                if prereqs:
                    prereq_names = [self.engine.ontology.sql_concepts.get(p, {}).get('label', p) for p in prereqs]
                    self.learning_display.insert(tk.END, f"   📚 Prerequisites: {', '.join(prereq_names)}\n", 'suggestion')
                
                self.learning_display.insert(tk.END, "\n")
        else:
            self.learning_display.insert(tk.END, "✅ Great job! No specific learning recommendations at this time.\n", 'success')
            self.learning_display.insert(tk.END, "Keep practicing to advance your SQL skills!\n")
        
        # Show available concepts
        self.learning_display.insert(tk.END, "\n" + "="*50 + "\n", 'header')
        self.learning_display.insert(tk.END, "📖 Available SQL Concepts in Ontology:\n\n", 'header')
        
        concepts_by_difficulty = sorted(
            self.engine.ontology.sql_concepts.values(),
            key=lambda x: x.get('difficulty', 1)
        )
        
        for concept in concepts_by_difficulty:
            difficulty_stars = "★" * concept.get('difficulty', 1)
            self.learning_display.insert(tk.END, f"• {concept['label']} {difficulty_stars}\n")
    
    def clear_query(self):
        """Clear the query editor"""
        self.query_editor.delete('1.0', tk.END)
        self.feedback_display.delete('1.0', tk.END)
        self.results_display.delete('1.0', tk.END)
        self.learning_display.delete('1.0', tk.END)
        self._show_welcome_message()
    
    def load_example(self):
        """Load an example query"""
        examples = [
            "SELECT * FROM employees",
            "SELECT department, AVG(salary) as avg_salary\nFROM employees\nGROUP BY department\nORDER BY avg_salary DESC",
            "SELECT first_name, last_name, salary\nFROM employees\nWHERE salary > 50000\nORDER BY salary DESC",
            "SELECT e.first_name, e.last_name, d.dept_name, d.location\nFROM employees e\nJOIN departments d ON e.department = d.dept_name\nWHERE e.salary > 60000",
            "SELECT department, COUNT(*) as employee_count\nFROM employees\nGROUP BY department\nHAVING COUNT(*) > 1\nORDER BY employee_count DESC"
        ]
        
        import random
        example = random.choice(examples)
        
        self.query_editor.delete('1.0', tk.END)
        self.query_editor.insert('1.0', example)
        messagebox.showinfo("Example Loaded", 
                          "Example query loaded!\n\nClick 'Analyze Query' to see the ontology-based analysis and results.")
    
    def run(self):
        """Start the application"""
        self.window.mainloop()


if __name__ == "__main__":
    # Make sure the ontology file exists
    ontology_file = "sql_tutor_ontology.owl"
    if not os.path.exists(ontology_file):
        print(f"⚠️ Ontology file '{ontology_file}' not found.")
        print("💡 Please make sure the OWL file is in the same directory as this script.")
        print("🚀 Starting with minimal ontology...")
    
    app = SQLTutorGUI(ontology_file)
    app.run()