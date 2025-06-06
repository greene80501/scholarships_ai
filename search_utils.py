import sqlite3
import json
import re # For GPA extraction
import logging
from flask import jsonify

logger = logging.getLogger(__name__)

class ScholarshipDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._check_db()

    def _check_db(self):
        # Basic check to see if the DB file exists, create if not (though schema needs to be separate)
        if not os.path.exists(self.db_path):
            logger.warning(f"Database file {self.db_path} not found. Application might not work correctly until DB is created and populated.")
            # In a real app, you might run a schema creation script here if the DB is truly empty.
            # For now, we assume a pre-existing DB.

    def get_connection(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error to {self.db_path}: {e}")
            raise # Re-raise the exception to be caught by the caller

# --- Data Inference Functions ---
def infer_field_of_study(scholarship):
    text_to_check = (
        str(scholarship.get('title', '')).lower() + ' ' +
        str(scholarship.get('eligibility_summary_text', '')).lower() + ' ' +
        str(scholarship.get('keywords_json', '')).lower() + ' ' + 
        str(scholarship.get('requirements_structured', {}).get('field_of_study', '')).lower() 
    )
    
    field_map = {
        'STEM': ['stem', 'science', 'technology', 'engineering', 'mathematics', 'computer', 'physics', 'chemistry', 'biology'],
        'Business': ['business', 'economics', 'finance', 'management', 'accounting', 'commerce', 'marketing'],
        'Arts & Humanities': ['arts', 'humanities', 'literature', 'creative', 'design', 'music', 'theater', 'philosophy', 'history', 'languages'],
        'Medicine & Health': ['medicine', 'medical', 'nursing', 'health', 'healthcare', 'pharmacy', 'dental', 'veterinary'], # Combined Medicine
        'Education': ['education', 'teaching', 'teacher', 'educational', 'pedagogy'],
        'Law & Justice': ['law', 'legal', 'justice', 'paralegal', 'criminology'] # Combined Law
    }

    inferred_fields = set()
    for display_field, keywords in field_map.items():
        if any(keyword in text_to_check for keyword in keywords):
            inferred_fields.add(display_field)
    
    if not inferred_fields: return 'All Fields'
    return ', '.join(sorted(list(inferred_fields)))


def infer_education_level(scholarship):
    text_to_check = (
        str(scholarship.get('title', '')).lower() + ' ' +
        str(scholarship.get('eligibility_summary_text', '')).lower() + ' ' +
        str(scholarship.get('requirements_structured', {}).get('education_level_required', '')).lower()
    )
    
    level_map = {
        'High School': ['high school', 'secondary', 'grade 9', 'grade 10', 'grade 11', 'grade 12', 'freshman student'], # freshman student can be ambiguous
        'Undergraduate': ['undergraduate', 'bachelor', 'college', 'associate', 'sophomore', 'junior', 'senior student'], # senior student can be ambiguous
        'Graduate': ['graduate', 'master', 'doctoral', 'phd', 'postgraduate'], 
    }
    
    inferred_levels = set()
    for display_level, keywords in level_map.items():
        if any(keyword in text_to_check for keyword in keywords):
            inferred_levels.add(display_level)
    
    if not inferred_levels: return 'All Levels'
    # Prioritize higher levels if multiple are inferred
    if 'Graduate' in inferred_levels: return 'Graduate'
    if 'Undergraduate' in inferred_levels: return 'Undergraduate'
    if 'High School' in inferred_levels: return 'High School'
    
    return ', '.join(sorted(list(inferred_levels))) # Fallback, should ideally be one of the above


def extract_gpa_requirement(scholarship):
    req_structured = scholarship.get('requirements_structured', {})
    if isinstance(req_structured, dict) and req_structured.get('gpa_minimum'):
        try:
            gpa_val_str = str(req_structured['gpa_minimum']).replace(',', '.') # Handle comma as decimal
            gpa_val = float(gpa_val_str)
            return f"{gpa_val:.1f}" # Format to one decimal place
        except (ValueError, TypeError):
            pass # Fall through to text extraction
    
    text_to_check = (
        str(scholarship.get('eligibility_summary_text', '')).lower() + ' ' +
        str(scholarship.get('title', '')).lower()
    )
    
    # More robust GPA patterns
    gpa_patterns = [
        r'(?:gpa|grade point average)\s*(?:of|is|:|minimum|at least|required)?\s*([1-4](?:[.,]\d{1,2})?|[0][.,]\d{1,2})', 
        r'([1-4](?:[.,]\d{1,2})?|[0][.,]\d{1,2})\s*(?:gpa|grade point average)', 
        r'minimum\s*([1-4](?:[.,]\d{1,2})?|[0][.,]\d{1,2})\s*(?:gpa|grade point average)?',
        r'([1-4](?:[.,]\d{1,2})?)\s*on a\s*4\.0\s*scale' # e.g. "3.0 on a 4.0 scale"
    ]

    highest_gpa_found = 0.0
    found = False

    for pattern in gpa_patterns:
        matches = re.finditer(pattern, text_to_check)
        for match in matches:
            gpa_str = match.group(1)
            if gpa_str:
                try:
                    # Normalize comma to period for float conversion
                    gpa_val = float(gpa_str.replace(',', '.'))
                    # Assuming GPA is usually on a 4.0 or 5.0 scale. Adjust if necessary.
                    if 0.0 <= gpa_val <= 5.0: 
                        highest_gpa_found = max(highest_gpa_found, gpa_val)
                        found = True
                except ValueError:
                    continue # Ignore if conversion fails
    
    return f"{highest_gpa_found:.1f}" if found else None


def infer_demographics(scholarship):
    text_to_check = (
        str(scholarship.get('title', '')).lower() + ' ' +
        str(scholarship.get('eligibility_summary_text', '')).lower() + ' ' +
        str(scholarship.get('requirements_structured', {}).get('demographics', '')).lower() 
    )
    
    demographics_map = {
        'Women': ['women', 'female', 'woman', 'girl'],
        'Minority': ['minority', 'ethnic', 'diversity', 'underrepresented', 'african american', 'black', 'hispanic', 'latino', 'latina', 'asian', 'native american', 'indigenous', 'pacific islander'],
        'First Generation': ['first generation', 'first-generation', '1st gen', 'first in family'],
        'International Students': ['international', 'foreign student', 'non-resident', 'non us citizen'], # Added non US citizen
        'Students with Disabilities': ['disability', 'disabled', 'special needs', 'ada', 'neurodivergent'], # Added neurodivergent
        'LGBTQ+': ['lgbt', 'lgbtq', 'lgbtqia', 'gay', 'lesbian', 'transgender', 'queer', 'bisexual', 'intersex', 'asexual'] # Expanded LGBTQ+
    }
    
    inferred_demographics = set()
    for display_demographic, keywords in demographics_map.items():
        if any(keyword in text_to_check for keyword in keywords):
            inferred_demographics.add(display_demographic)
            
    return ', '.join(sorted(list(inferred_demographics))) if inferred_demographics else 'All Students'


# --- API Logic Functions ---
def api_search_scholarships(args, db_instance):
    """API endpoint for scholarship search"""
    try:
        query = args.get('q', '').strip()
        min_amount_str = args.get('min_amount', '').strip()
        min_amount = float(min_amount_str) if min_amount_str else None
        deadline = args.get('deadline', '').strip()
        education_level = args.get('level', '').strip()
        field_of_study = args.get('field', '').strip()
        gpa_requirement_str = args.get('gpa', '').strip()
        gpa_requirement = None
        if gpa_requirement_str:
            try:
                gpa_requirement = float(gpa_requirement_str)
            except ValueError:
                logger.warning(f"Invalid GPA value received: {gpa_requirement_str}")

        demographics = args.get('demographics', '').strip()
        amount_range = args.get('amount_range', '').strip()
        sort_by = args.get('sort', 'relevance')
        page = args.get('page', 1, type=int)
        per_page = min(args.get('per_page', 20, type=int), 100) # Max 100 per page
        
        conditions = []
        params = []
        
        # Query building (similar to original, but ensure safety and clarity)
        if query:
            conditions.append('''(
                LOWER(title) LIKE ? OR 
                LOWER(organization_name) LIKE ? OR 
                LOWER(eligibility_summary_text) LIKE ? OR
                LOWER(keywords_json) LIKE ? OR
                LOWER(description_summary) LIKE ?
            )''') 
            query_param = f"%{query.lower()}%"
            params.extend([query_param] * 5) # Adjusted for 5 fields
        
        if min_amount is not None:
            conditions.append('(COALESCE(amount_numeric_min, amount_numeric_max, 0) >= ?)')
            params.append(min_amount)
        
        if deadline: # Assumes deadline is YYYY-MM-DD
            conditions.append('date(due_date) >= date(?)') # Ensure date comparison
            params.append(deadline)
        
        # Education Level Filter
        if education_level and education_level != 'all' and education_level != "":
            level_keywords_map = {
                'high-school': ['high school', 'secondary', 'grade 9', 'grade 10', 'grade 11', 'grade 12'],
                'undergraduate': ['undergraduate', 'bachelor', 'college', 'associate'],
                'graduate': ['graduate', 'master', 'doctoral', 'phd', 'postgraduate'], # Merged
                'doctoral': ['doctoral', 'phd', 'post-doctoral'] # Specific doctoral
            }
            if education_level in level_keywords_map:
                level_condition_parts = []
                for keyword in level_keywords_map[education_level]:
                    # Search in structured JSON, eligibility text, and title
                    level_condition_parts.append('LOWER(requirements_structured_json) LIKE ?')
                    params.append(f'%"{keyword}"%') # JSON keyword needs to be exact match within quotes
                    level_condition_parts.append('LOWER(eligibility_summary_text) LIKE ?') 
                    params.append(f"%{keyword}%")
                    level_condition_parts.append('LOWER(title) LIKE ?') 
                    params.append(f"%{keyword}%")
                if level_condition_parts:
                    conditions.append(f'({" OR ".join(level_condition_parts)})')

        # Field of Study Filter
        if field_of_study and field_of_study != 'all' and field_of_study != "":
            field_keywords_map = {
                'stem': ['science', 'technology', 'engineering', 'mathematics', 'computer', 'physics', 'biology', 'chemistry', 'stem'],
                'business': ['business', 'economics', 'finance', 'management', 'accounting', 'commerce', 'marketing'],
                'arts': ['arts', 'humanities', 'literature', 'creative', 'design', 'music', 'theater', 'philosophy', 'history', 'languages'],
                'medicine': ['medicine', 'medical', 'nursing', 'health', 'healthcare', 'pharmacy', 'dental', 'veterinary'],
                'education': ['education', 'teaching', 'teacher', 'educational', 'pedagogy'],
                'law': ['law', 'legal', 'justice', 'paralegal', 'criminology']
            }
            if field_of_study in field_keywords_map:
                field_condition_parts = []
                for keyword in field_keywords_map[field_of_study]:
                    field_condition_parts.append('LOWER(requirements_structured_json) LIKE ?')
                    params.append(f'%"{keyword}"%') # JSON keyword
                    field_condition_parts.append('LOWER(keywords_json) LIKE ?')
                    params.append(f'%"{keyword}"%') # JSON keyword in keywords list
                    field_condition_parts.append('LOWER(eligibility_summary_text) LIKE ?')
                    params.append(f"%{keyword}%")
                    field_condition_parts.append('LOWER(title) LIKE ?')
                    params.append(f"%{keyword}%")
                if field_condition_parts:
                    conditions.append(f'({" OR ".join(field_condition_parts)})')
        
        # GPA Filter
        if gpa_requirement is not None:
            # This is tricky because GPA is often text. We try to match numbers.
            # A dedicated, indexed numeric GPA column would be much better.
            # For now, we search for the number in text fields.
            gpa_pattern_search = f"%{gpa_requirement}%" # e.g. "%3.0%"
            gpa_conditions = [
                'LOWER(requirements_structured_json) LIKE ?', # Search for "gpa_minimum": "3.0"
                'LOWER(eligibility_summary_text) LIKE ?'      # Search for "GPA of 3.0"
            ]
            params.extend([gpa_pattern_search, gpa_pattern_search])
            conditions.append(f'({" OR ".join(gpa_conditions)})')


        # Demographics Filter
        if demographics and demographics != 'all' and demographics != "":
            demo_keywords_map = {
                'minority': ['minority', 'diversity', 'ethnic', 'underrepresented', 'african american', 'hispanic', 'asian', 'native american'],
                'women': ['women', 'female', 'woman'],
                'first-gen': ['first generation', 'first-generation', '1st gen'],
                'international': ['international', 'foreign student', 'non-resident']
            }
            if demographics in demo_keywords_map:
                demo_condition_parts = []
                for keyword in demo_keywords_map[demographics]:
                    demo_condition_parts.append('LOWER(eligibility_summary_text) LIKE ?')
                    params.append(f"%{keyword}%")
                    demo_condition_parts.append('LOWER(requirements_structured_json) LIKE ?')
                    params.append(f'%"{keyword}"%') # JSON keyword
                    demo_condition_parts.append('LOWER(title) LIKE ?')
                    params.append(f"%{keyword}%")
                if demo_condition_parts:
                    conditions.append(f'({" OR ".join(demo_condition_parts)})')
        
        # Amount Range Filter
        if amount_range and amount_range != 'all' and amount_range != "":
            amount_val_expr = 'COALESCE(amount_numeric_max, amount_numeric_min, 0)'
            if amount_range == '0-1000': conditions.append(f'({amount_val_expr} > 0 AND {amount_val_expr} <= 1000)')
            elif amount_range == '1000-5000': conditions.append(f'({amount_val_expr} > 1000 AND {amount_val_expr} <= 5000)')
            elif amount_range == '5000-10000': conditions.append(f'({amount_val_expr} > 5000 AND {amount_val_expr} <= 10000)')
            elif amount_range == '10000-25000': conditions.append(f'({amount_val_expr} > 10000 AND {amount_val_expr} <= 25000)')
            elif amount_range == '25000+': conditions.append(f'({amount_val_expr} > 25000)')
        
        # Construct SQL Query
        base_query_sql = 'SELECT * FROM scholarships'
        count_query_sql = 'SELECT COUNT(*) FROM scholarships'
        
        where_clause = ''
        if conditions:
            where_clause = ' WHERE ' + ' AND '.join(conditions)
        
        base_query_sql += where_clause
        count_query_sql += where_clause
        
        # Sorting Options
        sort_options = {
            'relevance': 'ORDER BY last_updated DESC, title ASC', # Default if no query, or by FTS rank if query
            'deadline': '''ORDER BY 
                CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END,
                date(due_date) ASC, 
                last_updated DESC''', 
            'amount': 'ORDER BY COALESCE(amount_numeric_max, amount_numeric_min, 0) DESC, last_updated DESC',
            'newest': 'ORDER BY last_updated DESC'
        }
        # If FTS5 is used and query is present, relevance sort would be different (e.g., ORDER BY rank)
        # For simple LIKE, 'relevance' is often by last_updated or title.
        base_query_sql += ' ' + sort_options.get(sort_by, sort_options['relevance'])
        
        conn = db_instance.get_connection()
        cursor = conn.cursor()
        
        logger.debug(f"Count SQL: {count_query_sql} with params: {params}")
        cursor.execute(count_query_sql, params)
        total_results = cursor.fetchone()[0]
        
        offset = (page - 1) * per_page
        paginated_query_sql = base_query_sql + f' LIMIT {per_page} OFFSET {offset}'
        
        logger.debug(f"Paginated SQL: {paginated_query_sql} with params: {params}")
        cursor.execute(paginated_query_sql, params)
        scholarships_rows = cursor.fetchall()
        
        conn.close()
        
        scholarship_list = []
        for scholarship_row in scholarships_rows:
            scholarship_dict = dict(scholarship_row)
            try: scholarship_dict['requirements_structured'] = json.loads(scholarship_dict.get('requirements_structured_json', '{}') or '{}')
            except (json.JSONDecodeError, TypeError): scholarship_dict['requirements_structured'] = {}
            try: scholarship_dict['keywords'] = json.loads(scholarship_dict.get('keywords_json', '[]') or '[]')
            except (json.JSONDecodeError, TypeError): scholarship_dict['keywords'] = []
            
            # Apply inference functions
            scholarship_dict['field_of_study'] = infer_field_of_study(scholarship_dict)
            scholarship_dict['education_level'] = infer_education_level(scholarship_dict)
            scholarship_dict['gpa_requirement'] = extract_gpa_requirement(scholarship_dict)
            scholarship_dict['demographic_requirements'] = infer_demographics(scholarship_dict)
            
            scholarship_list.append(scholarship_dict)
        
        # Return applied filters to the frontend
        returned_filters = {
            'q': query, 'min_amount': min_amount_str, 'deadline': deadline,
            'level': education_level, 'field': field_of_study, 'gpa': gpa_requirement_str, 
            'demographics': demographics, 'amount_range': amount_range
        }

        return jsonify({
            'success': True,
            'scholarships': scholarship_list,
            'pagination': {
                'current_page': page, 'per_page': per_page, 'total_results': total_results,
                'total_pages': (total_results + per_page - 1) // per_page if total_results > 0 else 0
            },
            'filters': returned_filters
        })
        
    except sqlite3.Error as sql_e:
        logger.error(f"SQLite error in API search: {str(sql_e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'A database error occurred.', 'message': str(sql_e)}), 500
    except Exception as e:
        logger.exception(f"Error in API search: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.', 'message': str(e)}), 500


def get_scholarship_detail_by_id(scholarship_id, db_instance):
    try:
        conn = db_instance.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM scholarships WHERE id = ?', (scholarship_id,))
        scholarship_row = cursor.fetchone()
        conn.close()
        
        if not scholarship_row:
            return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
        
        scholarship_dict = dict(scholarship_row)
        try: scholarship_dict['requirements_structured'] = json.loads(scholarship_dict.get('requirements_structured_json', '{}') or '{}')
        except (json.JSONDecodeError, TypeError): scholarship_dict['requirements_structured'] = {}
        try: scholarship_dict['keywords'] = json.loads(scholarship_dict.get('keywords_json', '[]') or '[]')
        except (json.JSONDecodeError, TypeError): scholarship_dict['keywords'] = []

        # Apply inference functions
        scholarship_dict['field_of_study'] = infer_field_of_study(scholarship_dict)
        scholarship_dict['education_level'] = infer_education_level(scholarship_dict)
        scholarship_dict['gpa_requirement'] = extract_gpa_requirement(scholarship_dict) 
        scholarship_dict['demographic_requirements'] = infer_demographics(scholarship_dict)
        
        return jsonify({'success': True,'scholarship': scholarship_dict})
    except sqlite3.Error as sql_e:
        logger.error(f"SQLite error getting scholarship detail: {str(sql_e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Database error fetching detail.'}), 500
    except Exception as e:
        logger.exception(f"Error getting scholarship detail: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500


def get_application_stats(db_instance):
    try:
        conn = db_instance.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM scholarships')
        total_scholarships = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT SUM(COALESCE(amount_numeric_max, amount_numeric_min, 0)) 
            FROM scholarships 
            WHERE amount_numeric_max IS NOT NULL OR amount_numeric_min IS NOT NULL OR amount_display IS NOT NULL 
        ''') 
        total_amount_row = cursor.fetchone()
        total_amount = total_amount_row[0] if total_amount_row and total_amount_row[0] is not None else 0
        
        # Placeholder for students_helped - this would ideally come from another source or calculation
        students_helped = int(4126) 
        
        conn.close()
        return jsonify({
            'success': True,
            'stats': {
                'total_scholarships': total_scholarships,
                'total_amount': int(total_amount), # Ensure it's an int
                'students_helped': students_helped
            }
        })
    except sqlite3.Error as sql_e:
        logger.error(f"SQLite error getting stats: {str(sql_e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Database error fetching stats.'}), 500
    except Exception as e:
        logger.exception(f"Error getting stats: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

# Need to import os for ScholarshipDatabase path check
import os