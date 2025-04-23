#!/usr/bin/env python3

import argparse

import requests

base_url = 'https://www.ebi.ac.uk/ols4/api'
query_fields = ['label', 'synonym', 'description', 'short_form', 'obo_id', 'annotations', 'logical_description', 'iri']
field_list = ['iri', 'label', 'short_form', 'obo_id', 'ontology_name', 'ontology_prefix', 'description', 'type',
              'synonym', 'annotations', 'logical_description']


def is_in_efo(iri):
    term_url = f'{base_url}/ontologies/efo/terms/{iri}'
    response = requests.get(term_url)
    if response.status_code == 200:
        return True
    else:
        return False

def format_outout(ontology_result, is_in_efo):
    output = f"{ontology_result['iri']}|{ontology_result['label']}|||"
    if is_in_efo:
        return output + 'EFO_CURRENT', 'DONE', f'{",".join(ontology_result["exact_match"])}'
    else:
        return output , 'IMPORT', f'{",".join(ontology_result["exact_match"])}'

def add_fields_with_exact_match(ontology_result, search_term):
    # Where was the match found ?
    found_in = []
    for field in query_fields:
        if field in ontology_result:
            if isinstance(ontology_result[field], str) and search_term.lower() in ontology_result[field].lower():
                found_in.append(field)
            if isinstance(ontology_result[field], list):
                if [element for element in ontology_result[field] if search_term.lower() in element.lower()]:
                    found_in.append(field)
    ontology_result['exact_match'] = found_in

def search_ols4(term):
    search_url = base_url + "/search"
    params = {
        'q': term,
        'exact': 'true',
        'ontologies': 'efo,mondo,hp',
        'queryFileds': ','.join(query_fields),
        'fieldList': ','.join(field_list)
    }

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json()

        if results['response']['numFound'] > 0:
            ontology_to_term = {}

            for result in results['response']['docs']:
                add_fields_with_exact_match(result, term)
                if result['exact_match']:
                    ontology_to_term[result.get('ontology_name')] = result
            if 'efo' in ontology_to_term:
                return format_outout(ontology_to_term['efo'], True)
                # return (ontology_to_term['efo'] + 'EFO_CURRENT', 'DONE')
            elif 'mondo' in ontology_to_term:
                return format_outout(ontology_to_term['mondo'], is_in_efo(ontology_to_term['mondo']['iri']))
            elif 'hp' in ontology_to_term:
                return format_outout(ontology_to_term['hp'], is_in_efo(ontology_to_term['hp']['iri']))
        return '', '', ''

    except requests.RequestException as e:
        print(f"Error querying OLS4: {e}")
        return None, None, None

def main():
    parser = argparse.ArgumentParser('Search OLS label for exact match')
    parser.add_argument('--search_file', type=str, help="path to a file containing the search terms. One per line")
    parser.add_argument('--output_file', type=str, help="path to the output file with the results. One per line")

    args = parser.parse_args()
    count = 0
    with open(args.search_file) as open_input, open(args.output_file, 'w') as open_output:
        for line in open_input:
            result, status, comment = search_ols4(line.strip())
            open_output.write(f'{line.strip()}\t{result}\t{status}\t{comment}\n')
            count += 1
            if count % 100 == 0:
                print(f'Processed {count} lines')


if __name__ == '__main__':
    main()

