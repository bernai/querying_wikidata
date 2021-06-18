import itertools
import sys
import threading
import time
import requests
import json
import webbrowser

endpoint_url = "https://query.wikidata.org/sparql"
user_agent = "UZH_SemanticWeb_CourseProject/%s.%s" % (sys.version_info[0], sys.version_info[1])


def get_results_request(query):
    """
    Gets the results from wikidata through a SPARQL query.
    """
    req = requests.get(endpoint_url, params={'format': 'json', 'query': query}, headers={'User-Agent': user_agent}).text
    return json.loads(req)


def input_checker(inp: str, start: int = 1, stop: int = 7) -> int:
    """
    Checks whether input can be turned into an integer and is in specified interval.
    """
    wrong_input = True
    while wrong_input:
        try:
            inp = int(inp)
            while not stop >= inp >= start:
                inp = input(f'Input not an integer between {start} and {stop}. Please try again:\n'
                            '>> ')  # error if not in specified interval
                inp = int(inp)   # error if not able to turn into integer
            wrong_input = False

        except ValueError:
            inp = input(f'"{inp}" is not an integer. Please try again:\n'
                        f'>> ')
    return inp


def find_by_id(genre_str, genre_id):
    """
    Finds Wikidata entity through its entity ID given by the user.
    """
    i_4 = 2
    item_label = ''

    i_3 = input('\nEnter an Entity ID:\n'
                '>> ').rstrip()

    try:
        # QUERY 2: find film by ID
        query = """
        SELECT ?film ?filmLabel 
        WHERE 
        {
          VALUES ?film {wd:%s} # set film variable using ID provided by user
          ?film wdt:P31/wdt:P279* wd:Q11424; # make sure this ID belongs to film
                wdt:P136 wd:%s. # make sure it belongs to previously selected genre
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        """ % (i_3, genre_id)

        results = get_results_request(query)

        entity_id = results['results']['bindings'][0]['film']['value'][31:]
        item_label = results['results']['bindings'][0]['filmLabel']['value']

        i_4 = input_checker(input(f'\nDid you mean "{item_label}" with Entity ID "{entity_id}"?:\n'
                                  f'[1] yes [2] no\n'
                                  f'>> '), 1, 2)

    except IndexError:
        print(f'\n"{i_3}" is not an ID for any {genre_str}, try something else.')

    return i_4, i_3, item_label


def find_by_string(genre_str, genre_id):
    """
    Finds Wikidata entity that contains the string given by the user.
    """
    i_4 = 2
    entity_id = ''
    item_label = ''

    i_3 = input('\nEnter the Label (Name) of the film:\n'
                '>> ').lower()

    # QUERY 3: find labels that contain user given input, return first
    query = """
    SELECT ?film ?filmLabel
    WHERE{
    ?film wdt:P31 wd:Q11424;
            wdt:P136 wd:%s; # make sure film belongs to specified genre
            rdfs:label ?filmLabel. # get labels
    FILTER(LANG(?filmLabel) ="en"). # only get english labels
    FILTER (CONTAINS(LCASE(STR(?filmLabel)), "%s"))  # check if user input is somewhere in label
    } LIMIT 1 # return only one out of all that contain this string
    """ % (genre_id, i_3)

    results = get_results_request(query)

    try:
        entity_id = results['results']['bindings'][0]['film']['value'][31:]
        item_label = results['results']['bindings'][0]['filmLabel']['value']

        i_4 = input_checker(input(f'\nDid you mean "{item_label}" with Entity ID "{entity_id}"?:\n'
                                  f'[1] yes [2] no\n'
                                  f'>> '), 1, 2)

    except IndexError:
        print(f'\nCannot find any {genre_str} title that contains "{i_3}", try something else.')

    return i_4, entity_id, item_label


# chose to implement limit here to avoid constant new queries for limit and offset
def print_request(results, start=0, limit=5):
    print(f'\033[1m{"Entity ID":<15s} {"Label":<10s}\033[0m')  # ANSI escape sequence for bold header
    counter = start
    while counter < limit:
        for item in results['results']['bindings'][start:limit]:
            entity_id = item['film']['value'][31:]
            item_label = item['filmLabel']['value']
            print(f'{entity_id:<15s} {item_label:<10s}')
            counter += 1


def main():
    restart = True  # last input of program asks whether user wants to restart, while true program will continue

    while restart:
        i = input_checker(input(f'\nSelect a film genre. Enter an integer between 1 and 7 to select an option: \n'
                                f'[1] action [2] adventure [3] drama [4] comedy [5] documentary [6] thriller [7] '
                                f'romance\n '
                                f'>> '))

        film_id_genre_dict = {1: ('action film', 'Q188473'), 2: ('adventure film', 'Q319221'), 3: ('drama film', 'Q130232'),
                              4: ('comedy film', 'Q157443'), 5: ('documentary film', 'Q93204'),
                              6: ('thriller film', 'Q2484376'),
                              7: ('romance film', 'Q1054574')}

        genre_str = film_id_genre_dict[i][0]
        film_genre_id = film_id_genre_dict[i][1]

        # look for all instances/subclasses of film and show the ones that have the selected genre as property
        # this string formatting method instead f-string as brackets are present;
        # no LIMIT on purpose to get everything without additional requests if user requests;

        # QUERY 1: film that belongs to certain genre
        query = """
        SELECT ?film ?filmLabel
        WHERE {
        ?film wdt:P31/wdt:P279* wd:Q11424; # variable is instance/subclass of film
              wdt:P136 wd:%s. # variable film has certain genre
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        """ % film_genre_id

        print(f'\nHere are 10 {genre_str}s as an overview:')

        done = False

        # print Loading... while request not finished as first one takes longest
        def loading():
            # idea from a thread on stackoverflow, slightly adapted: https://stackoverflow.com/a/22029635
            for dot in itertools.cycle(['', '.', '..', '...']):
                if done:
                    break
                sys.stdout.write('\rLoading' + dot)
                sys.stdout.flush()
                time.sleep(1)

        t = threading.Thread(target=loading)
        t.start()
        results = get_results_request(query)  # first query might take a while, also depending on connection
        sys.stdout.write('\r' + '')
        done = True

        print_request(results, 0, 10)

        i_2 = input_checker(input(f'\nEnter an integer to select an option:\n'
                                  f'[1] query with specific entity [2] query on all {genre_str}s\n'
                                  f'>> '), 1, 2)

        if i_2 == 1:
            offset = 0

            i_3 = input_checker(input(f'\nSelection of the {genre_str}:\n'
                                      f'[1] Enter Entity ID [2] Enter Label/Name of any {genre_str}  '
                                      f'[3] Show more {genre_str}s\n'
                                      f'>> '), 1, 3)

            while i_3 == 3:
                print(f'\nMore {genre_str}s:')
                offset += 10

                # reuse results of QUERY 1 with added offset in python
                print_request(results, offset, offset + 10)

                i_3 = input_checker(input(f'\nSelection of the {genre_str}:\n'
                                          f'[1] Enter Entity ID [2] Enter Label/Name of any {genre_str} '
                                          f'[3] Show more {genre_str}s\n'
                                          f'>> '), 1, 3)

            if i_3 == 1:
                i_4 = 2
                while i_4 == 2:

                    # QUERY 2: find film by ID
                    i_4, entity_id, item_label = find_by_id(genre_str, film_genre_id)

            if i_3 == 2:
                i_4 = 2
                while i_4 == 2:

                    # QUERY 3: find labels that contain user given input, return first
                    i_4, entity_id, item_label = find_by_string(genre_str, film_genre_id)

            restart_single = True
            while restart_single:
                i_5 = input_checker(input(f'\nEnter an integer to select an option for "{item_label}":\n'
                                          f'[1] Show average age of all cast members at the first publication date\n'
                                          f'[2] Show sex/gender count among all cast members \n'
                                          f'[3] Show difference between box office takings and cost of film\n'
                                          f'[4] List all other films by the same director(s)\n'
                                          f'>> '), 1, 4)

                if i_5 == 1:
                    # QUERY 4: average age of all cast members at the first publication date
                    query = """
                    SELECT (AVG(?age_first_publ) AS ?avg) { # take ages at first publication and average them
                    # return these variables, take maximum age (as sometimes multiple publication dates are available)
                    SELECT ?cast_member ?cast_memberLabel (MAX(?age) AS ?age_first_publ) 
                    WHERE 
                    { # set user film ID input as film variable
                      VALUES ?film {wd:%s} # no check for genre needed as it was done already in query 2/3
                      ?film wdt:P161 ?cast_member; # get cast members
                            wdt:P577 ?pub_date. # get publication date of film
                      ?cast_member wdt:P569 ?birth_date. # get birth date of cast member
                      BIND(YEAR(?pub_date) - YEAR(?birth_date) as ?age)
                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        
                      }
                    GROUP BY ?cast_member ?cast_memberLabel ?total ?avg
                    }
                    """ % entity_id

                    results = get_results_request(query)

                    avg_age = results["results"]["bindings"][0]["avg"]["value"][:5]
                    if avg_age == "0":
                        print(f'\nThere is no data about the cast members of "{item_label}". '
                              f'Cannot calculate average age.')
                    else:
                        print(f'\nAverage age for cast members in "{item_label}" is '
                              f'{avg_age}')

                if i_5 == 2:
                    # QUERY 5: show sex/gender count of cast members
                    # also handles cases where more than one sex/gender property given by listing everything
                    query = """
                    SELECT ?sex_gender_list (COUNT(?sex_gender_list) AS ?count) { # count how many of each label
                      # create list of concatenated labels, as e.g. someone can be non-binary as well as transgender
                      # so we take this as one label
                      SELECT ?cast_memberLabel (GROUP_CONCAT(DISTINCT ?genderLabel; SEPARATOR = ", ") AS ?sex_gender_list) 
                      WHERE {
                        VALUES ?film {wd:%s}
                        ?film wdt:P161 ?cast_member.
                        ?cast_member wdt:P21 [rdfs:label ?genderLabel]. # get sex/gender labels of cast members
                        FILTER((LANG(?genderLabel)) = "en") # only english sex/gender labels
                        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". } # get labels for rest
                      }
                      GROUP BY ?cast_memberLabel ?count # group by needed for group concat
                    }
                    GROUP BY ?sex_gender_list ?count # group by needed for count
                    """ % entity_id

                    results = get_results_request(query)

                    print(f'\n\033[1m{"Count":<15s} {"Label":<10s}\033[0m')
                    for item in results["results"]["bindings"]:
                        label = item['sex_gender_list']['value']
                        count = item['count']['value']
                        print(f'{count:<15s} {label:<10s}')

                if i_5 == 3:
                    # QUERY 6: show box office takings and cost and calculate their difference if
                    # they are in the same currency:
                    query = """
                    SELECT (MAX(?box_office) AS ?box) ?cost ((?box - ?cost) AS ?difference) ?cost_unitLabel
                    WHERE {
                      VALUES ?film{wd:%s}
                      ?film wdt:P2142 ?box_office; # box office takings of film
                            p:P2142 [psv:P2142 ?box_node]; # get node for box office takings
                            wdt:P2130 ?cost; # cost of film
                            p:P2130 [psv:P2130 ?cost_node]. # get node of cost
                      ?cost_node wikibase:quantityUnit ?cost_unit. # get currency of cost
                      ?box_node wikibase:quantityUnit ?box_unit. # get currency of box office takings
                      FILTER (?cost_unit = ?box_unit) # only take those with same currency as otherwise not comparable
                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
                    }
                    GROUP BY ?box ?cost ?difference ?cost_unitLabel 
                    """ % entity_id

                    results = get_results_request(query)

                    if len(results['results']['bindings']) == 0:
                        print(f'\nUnfortunately, "{item_label}" does not have information about both box office \n'
                              f'takings and cost or has both in different currencies. Cannot calculate difference.')

                    else:
                        print(f'\n\033[1m{"Difference":<15s} {"Box Office":<15s} {"Cost":<15s} {"Currency":<15s}\033[0m')
                        box = int(results['results']['bindings'][0]['box']['value'])
                        cost = int(results['results']['bindings'][0]['cost']['value'])
                        diff = int(results['results']['bindings'][0]['difference']['value'])
                        cur = results['results']['bindings'][0]['cost_unitLabel']['value']
                        print(f'{diff:<15,d} {box:<15,d} {cost:<15,d} {cur:<15s}')

                if i_5 == 4:
                    # QUERY 7: list director(s) of this film with all their other films
                    query = """
                    # tilde as a separator to avoid splitting at comma in film title within python
                    # create list including all films except for current selected one by director
                    SELECT ?directorLabel (GROUP_CONCAT(DISTINCT ?other_filmLabel; SEPARATOR = " ~ ") AS ?film_list) (COUNT(DISTINCT ?other_filmLabel) AS ?count) 
                    WHERE {
                      VALUES ?film {wd:%s}
                      ?film wdt:P57 ?director. # director variable
                      ?other_film wdt:P57 ?director; # other films need to have the same director
                                  wdt:P31/wdt:P279* wd:Q11424;
                                  rdfs:label ?other_filmLabel. # get labels of other films
                      FILTER(?other_film != ?film) # sort out our current film selected by user
                      FILTER((LANG(?other_filmLabel)) = "en") # get english labels only
                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
                    }
                    GROUP BY ?directorLabel # group by director for group concat
                    """ % entity_id

                    results = get_results_request(query)

                    if len(results['results']['bindings']) == 0:
                        print(f'\nUnfortunately, "{item_label}" does not have information about its director(s). \n')

                    else:
                        print(f'\n\033[1m{"Director":<20s} {"Amount":<15s} {"Films":<15s}\033[0m')
                        for item in results["results"]["bindings"]:
                            director = item['directorLabel']['value']
                            count = item['count']['value']
                            films = item['film_list']['value']
                            # split for cleaner formatting output
                            split_films = [film for film in films.split(' ~ ')]
                            start = 0
                            stop = 4
                            combined_list = []
                            for i in range(int(len(split_films)/4)+1):  # prevent cutting off if float gets rounded down
                                combined_list.append(', '.join(split_films[start:stop]))
                                start += 4
                                stop += 4

                            print(f'\n{director:<20s} {count:<15s} {combined_list[0]:<15s}')

                            for films in combined_list[1:]:
                                print(f'{"":<20s} {"":<15s} {films:<15s}')

                restart_single = (1 == input_checker(input(f'\nDo you want to select another option for "{item_label}"?'
                                                           f'\n[1] Yes [2] No\n'
                                                           f'>>  '), 1, 2))

        if i_2 == 2:
            restart_all = True
            while restart_all:

                i_3 = input_checker(input(f'\nEnter an integer to select an option for all {genre_str}s:\n'
                                          f'[1] show top 10 who won most awards\n'
                                          f'[2] show filming locations of all on a map '
                                          f'(this option will open your browser)\n'
                                          f'[3] show birthplace of swiss cast members on a map'
                                          f'\n\twith the {genre_str}s'
                                          f' they were part of (this option will open your browser)\n'
                                          f'[4] show top 10 with biggest difference between\n\tbox office takings '
                                          f'and cost (in USD)\n'
                                          f'>> '), 1, 4)

                if i_3 == 1:
                    # QUERY 8: count awards of films, get top 10
                    query = """
                    SELECT ?film ?filmLabel (COUNT(?award) AS ?count) # count how many awards are returned per film
                    WHERE {
                      ?film wdt:P31/wdt:P279* wd:Q11424;
                            wdt:P136 wd:%s;
                            wdt:P166 ?award. # awards of a film
                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
                    }
                    GROUP BY ?film ?filmLabel
                    ORDER BY DESC(?count) # order by most award first
                    LIMIT 10 # return top 10
                    """ % film_genre_id

                    results = get_results_request(query)

                    print(f'\nHere are the {genre_str}s with the most awards:')
                    print(f'\033[1m{"Awards":<10s} {"Entity ID":<15s} {"Label":<10s}\033[0m')
                    for item in results['results']['bindings']:
                        entity_id = item['film']['value'][31:]
                        item_label = item['filmLabel']['value']
                        count = item['count']['value']
                        print(f'{count:<10s} {entity_id:<15s} {item_label:<10s} ')

                if i_3 == 2:
                    # query is directly included in url with specified film genre
                    # difficult to plot everything within a map in python / cleaner view on wikidata query service

                    # QUERY 9 show filming locations on map:
                    url_map = f"https://query.wikidata.org/embed.html#%23defaultView%3AMap%7B%22hide%22%3A%20%22%3Fcoords%22%7D%20%23%20this%20is%20for%20hiding%20coordinates%20in%20output%20of%20map%0ASELECT%20DISTINCT%20%3Ffilm%20%3FfilmLabel%20%3Fcoords%20%0AWHERE%20%7B%0A%3Ffilm%20wdt%3AP31%2Fwdt%3AP279*%20wd%3AQ11424%3B%20%0A%20%20%20%20%20%20%20%20%20%20%20%20%20%20wdt%3AP136%20wd%3A{film_genre_id}%3B%20%23%20films%20belonging%20to%20specific%20genre%0A%20%20%20%20%20%20%20wdt%3AP915%20%5Bwdt%3AP625%20%3Fcoords%5D.%20%23%20get%20coordinates%20of%20location%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D"
                    webbrowser.open(url_map)

                if i_3 == 3:
                    # query directly included in url
                    # QUERY 10: cast members who were born in switzerland and the films they have worked on as list
                    url_map = f"https://query.wikidata.org/embed.html#%23defaultView%3AMap%7B%22hide%22%3A%20%22%3Fcoordinates%22%7D%20%23%C2%A0hide%20coordinates%20from%20output%0ASELECT%20%3Fcast_member%20%3Fcast_memberLabel%20%3Fcoordinates%20%3Ffilm_listLabel%20WHERE%20%7B%0A%20%20%7B%0A%20%20%20%20%23%20concatenate%20all%20films%20cast%20member%20was%20part%0A%20%20%20%20SELECT%20%3Fcast_member%20%3Fcoordinates%20(GROUP_CONCAT(DISTINCT%20%3FfilmLabel%3B%20SEPARATOR%20%3D%20%22%2C%20%22)%20AS%20%3Ffilm_list)%20WHERE%20%7B%0A%20%20%0A%20%20%20%20%3Ffilm%20wdt%3AP31%2Fwdt%3AP279*%20wd%3AQ11424%3B%0A%20%20%20%20%20%20%20%20%20%20wdt%3AP136%20wd%3A{film_genre_id}%3B%0A%20%20%20%20%20%20%20%20%20%20wdt%3AP161%20%3Fcast_member%3B%20%23%20cast%20member%0A%20%20%20%20%20%20%20%20%20%20rdfs%3Alabel%20%3FfilmLabel.%20%23%20get%20film%20label%0A%20%20%20%20FILTER((LANG(%3FfilmLabel))%20%3D%20%22en%22)%20%23%20only%20get%20English%20labels%0A%20%20%20%20%3Fcast_member%20wdt%3AP27%20wd%3AQ39%3B%20%23%20cast%20member%20needs%20to%20be%20Swiss%0A%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20%20wdt%3AP19%20%5Bwdt%3AP625%20%3Fcoordinates%5D.%20%23%20get%20coordinates%20of%20place%20of%20birth%0A%20%20%20%20%7D%0A%20%20GROUP%20BY%20%3Fcast_member%20%3Fcoordinates%20%23%20group%20needed%20for%20concatenation%0A%20%20%7D%0A%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D%0A%0A%0A"
                    webbrowser.open(url_map)

                if i_3 == 4:
                    # altered version of QUERY 6  films with highest difference between box office takings and cost:
                    query = """
                    SELECT ?film ?filmLabel (MAX(?box_office) AS ?box) ?cost ((?box - ?cost) AS ?difference) ?cost_unitLabel
                    WHERE {
                      ?film wdt:P31/wdt:P279* wd:Q11424; 
                            wdt:P136 wd:%s;
                            wdt:P2142 ?box_office;
                            p:P2142 [psv:P2142 ?box_node]; 
                            wdt:P2130 ?cost;
                            p:P2130 [psv:P2130 ?cost_node].
                      ?cost_node wikibase:quantityUnit ?cost_unit. # get currency of cost
                      ?box_node wikibase:quantityUnit ?box_unit. # get currency of box office takings
                      VALUES ?usd{wd:Q4917} # define variable for USD
                      FILTER (?cost_unit = ?usd && ?box_unit = ?usd)  # only select the ones with USD for both
                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
                    }
                    GROUP BY ?film ?filmLabel ?box ?cost ?difference ?cost_unitLabel 
                    ORDER BY DESC(?difference) # biggest difference first
                    LIMIT 10 # return 10
                    """ % film_genre_id

                    results = get_results_request(query)

                    print(f'\n\033[1m{"Difference":<15s} {"Box Office":<15s} {"Cost":<15s} {"Entity ID":<15s} {"Label":<15s}'
                          f'\033[0m')
                    for item in results['results']['bindings']:
                        item_label = item['filmLabel']['value']
                        entity_id = item['film']['value'][31:]
                        box = int(item['box']['value'])
                        cost = int(item['cost']['value'])
                        diff = int(item['difference']['value'])
                        print(f'{diff:<15,d} {box:<15,d} {cost:<15,d} {entity_id:<15s} {item_label:<15s} ')

                restart_all = (1 == input_checker(input(f'\nDo you want to select another option for {genre_str}s?'
                                                        f'\n[1] Yes [2] No\n'
                                                        f'>>  '), 1, 2))

        restart = (1 == input_checker(input(f'\nRestart whole query?\n'
                                            f'[1] Yes [2] No\n'
                                            f'>>  '), 1, 2))


if __name__ == '__main__':
    main()
