import requests
import json
import csv
import string
import os

#THESE FUNCTIONS ARE NOT API CALLS -------------------------------------

def spFiltByTaxa(rank_names):
    #FILTERS 'globalSpeciesAssessment.csv' BY ONE OR MORE TAXA OF THE SAME RANK

    def spFiltByTaxon(rank, name):
        """TAKES RANK AND NAME, MAKES NEW FILTERED CSV, RETURNS LIST OF FILENAMES"""

        #READ FROM ONE CSV AND WRITE TO ANOTHER WITH THE SAME HEADERS
        target_name = 'global' + name.capitalize() + 'Assessment.csv'
        with open('globalSpeciesAssessment.csv', 'r') as source, open(target_name, 'w') as target:
            reader = csv.reader(source, delimiter=',')
            writer = csv.writer(target)
            writer.writerow(next(reader)) #copies header to target

            count = 0
            for row in reader:
                if row[rank] == name:
                    writer.writerow(row)
                    count += 1

            source.close()
            target.close()

        print('\nMade', target_name + ' with ' + str(count) + ' species')

        return target_name

    #REF: ['taxonid', 'kingdom_name', 'phylum_name', 'class_name', 'order_name', 'family_name', 'genus_name', 'scientific_name', 'infra_rank', 'infra_name', 'population', 'category']

    rank = 3
    files_spFiltByTaxa = []
    for name in rank_names:
        files_spFiltByTaxa.append(spFiltByTaxon(rank, name))

    print('\nFiles in dir for species filtered by taxonomy:')
    for f in files_spFiltByTaxa:
        print(' - ', f)


def getTaxaInCountries():
    """TAKES ALL SPECIES IN COUNTRY AND ALL SPECIES IN A TAXON AND RETURNS COMMON MEMBERS
       EITHER ENTITY CAN BE A SINGLETON OR A LIST"""

    def getTaxonInCountries(files_allSpByCountry, files_spFiltByTax, rank):
        """TAKES LIST OF CSVs OF ALL SPECIES IN COUNTRY AND GLOBAL CSV OF A RANK, MAKES CSV OF COMMON MEMBERS BY 'taxonid' RETURNS LIST OF FILES"""
        files_made = []

        for file in files_allSpByCountry:

            with open(file, 'r') as c, open(files_spFiltByTax, 'r') as s:
                filename = file[:3] + rank.capitalize() + file[3:5]
                files_made.append(filename)
                print('...Finding all', rank.lower(), 'in ' + file[3:5])

                with open(filename + '.csv', 'w') as target:
                    country = csv.reader(c, delimiter=',')
                    species = csv.reader(s, delimiter=',')
                    writer = csv.writer(target)
                    writer.writerow(next(country)) # write header row from country to target
                    
                    country_list = [row for row in country]
                    species_list = [row for row in species]

                    count = 0
                    for sp in species_list:
                        for cn in country_list:
                            #sp[0] == cn[0] is correct but uses 'taxonid'
                            #sp[7] == cn[1] creates 'dupes' because subpops are ignored
                            if sp[0] == cn[0]:
                                writer.writerow(cn)
                                count += 1

                    print('Made', filename + '.csv with ' + str(count) + ' species\n')
                
                    c.close()
                    s.close()
                    target.close()

        return files_made

    #ASSUMES ALL SPECIES BY COUNTRY CSV EXISTS IN LOCAL DIR
    files_in_dir = os.listdir()
    files_allSpByCountry = [f for f in files_in_dir if f[:3] == 'all' and f[5:] == 'species.csv']

    #ASSUMES ALL SPECIES FILTERED BY TAXONOMY RANK CSV EXISTS IN LOCAL DIR
    files_spFiltByTaxon = [f for f in files_in_dir if f[:6] == 'global' and f[6:13] != 'Species']

    files_getTaxonInCountries = []
    for f in files_spFiltByTaxon:
        files_getTaxonInCountries.extend(getTaxonInCountries(files_allSpByCountry, f, f[6:-14]))
    
    print('\nFiles in dir for species filtered by taxonomy:')
    for f in files_getTaxonInCountries:
        print(' - ', f)


#THESE FUNCTIONS ARE API CALLS -----------------------------------------

def compileSpHabByCountries(STEM, TOKEN, hab_list):
    """MAKES HABITATS CSV FROM LIST OF 'allSpByCountries()' CSVs FOR ALL HABITATS
    ASSUMES ALL SPECIES BY COUNTRY CSV EXISTS IN LOCAL DIR"""

    def compileSpHabByCountry(hab_list, list_species, country_code):
        """TAKES LIST OF HABITATS, LIST OF SPECIES HABITATS DICTS, MAKES CSV"""
        
        #MAKES CSV WITH HEADERS ONLY
        filename = 'allSpeciesHabitats' + country_code + '.csv' #GENERALIZE ME
        with open(filename, 'w', newline='') as f:
            write = csv.DictWriter(f, fieldnames=hab_list)
            write.writeheader()
            f.close()

        for species in list_species:
            row_labels = {'scientific_name': species['scientific_name'], 'taxonid': species['id'], 'country': species['country']}

            #IF SPECIES IN HABITAT, MAKES DICT MAPPED TO HEADERS
            habitat_row = {}
            for h in hab_list:
                for s in species['result']:
                    if s['habitat'] in h:
                        in_habitat = {'suitability': s['suitability'], 'season': s['season'], 'majorimportance': s['majorimportance']}
                        habitat_row.update({h:in_habitat})
                    else:
                        habitat_row.update({h:None})

            habitat_row.update(row_labels)

            #APPENDS ROW TO CSV
            with open(filename, 'a', newline='') as f:
                write = csv.DictWriter(f, fieldnames=hab_list)
                write.writerow(habitat_row)
                f.close()


    files_in_dir = os.listdir()
    files_allSpByCountry = [name for name in files_in_dir if name[:3] == 'all' and name[5:] == 'species.csv']

    for name in files_allSpByCountry:
        with open(name, 'r') as f:
            reader = csv.reader(f)
            next(reader) #skips the first, header row
            list_species = []
            count = 1
            for row in reader:
                print(count, '\t...Processing', row[1], 'in', name[3:5])
                #CALLS API FOR EACH SPECIES-ROW IN CSV BY 'taxonid'
                response = requests.get(STEM + 'habitats/species/id/' + str(row[0]) + TOKEN)
                species_API_call = response.json()
                species_API_call.update({'scientific_name': row[1]})
                species_API_call.update({'country': name[3:5]})
                list_species.append(species_API_call)
                count += 1

        compileSpHabByCountry(hab_list, list_species, name[3:5])


def spFiltByHabsInCountries(hab_list):
    """TAKES LIST OF COUNTRIES AND FILTERS ALL SPECIES THAT EXIST IN GIVEN SUBHABITATS"""

    def spFiltByHabsInCountry(country, target_hab, hab_name):
        """TAKES SINGLETON ALL SP IN COUNTRY CSV, LIST OF TARGET HABITATS, HABITAT NAME STRING
           MAKES NEW CSV BASED ON FILTERED RESULT"""
        filename = 'all' + hab_name + country[-6:-4] + 'species.csv'
        with open(country, 'r', newline='') as f, open(filename, 'w', newline='') as g:
            reader = csv.reader(f)
            writer = csv.writer(g)
            writer.writerow(target_hab)
            next(reader)
            count = 1
            for row in reader:
              for r in row[8:13]:
                  if r:
                        good_row = row[:3] + row[8:13]
                        writer.writerow(good_row)
                        count += 1
            print('Made', filename, 'with', count, 'species')
            f.close()
            g.close()

    #CURRENTLY ONLY FORESTS ARE OF INTEREST SO I WON'T ABSTRACT ANY FURTHER
    FORESTS = hab_list[:3] + hab_list[8:13] #['1.5', '1.6', '1.7', '1.8', '1.9']
    WETLANDS = hab_list[:3] + hab_list[34:43] + hab_list[46:51] #['5.1', '5.2', '5.3', '5.4', '5.5', '5.6', '5.7', '5.8', '5.9', '5.13', '5.14', '5.15', '5.16', '5.17']
    DEGRADED = hab_list[:3] + hab_list[101:102] #['14.6']

    target_hab = FORESTS
    hab_name = 'Forests'

    files_in_dir = os.listdir()
    files_allSpeciesHabitatsByCountry = [f for f in files_in_dir if 'allSpeciesHabitats' in f]

    for f in files_allSpeciesHabitatsByCountry:
        spFiltByHabsInCountry(f, target_hab, hab_name)


def allSpByCountries(STEM, TOKEN, COUNTRIES):
    """TAKES STEM, TOKEN, LIST OF COUNTRIES, MAKES SPECIES-BY-COUNTRY TXT AND CSV FILES"""

    def allSpByCountry(STEM, TOKEN, filename, country):
        """MAKES API CALL AND WRITE THE TEXT FILE - DO THIS ONLY ONCE"""
        request = requests.get(STEM + 'country/getspecies/' + country + TOKEN)
        response = request.json()

        print()
        writeTXTFile(filename, response)

        #LOADS JSON FOR PARSING BY 'result', ADDS COUNTRY COLUMN
        with open(filename + '.txt', 'r') as f:
            contents = json.load(f)
            result = contents['result']
            for key in result:
                key.update({'country': country})
            f.close()
        print('...Parsing', filename, 'object')

        writeCSVFile(filename, result)

    files_allSpByCountry = []

    for c in COUNTRIES:
        filename = 'all' + c + 'species'
        allSpByCountry(STEM, TOKEN, filename, c)
        files_allSpByCountry.append(filename)

    print()
    print('Files in dir for all species by country:')
    for f in files_allSpByCountry:
        print(' - ', f)


def makeGlobSpAssesment(STEM, TOKEN):
    """TAKES STEM, TOKEN AND RETURNS LIST OF FILENAMES
       MAKES API CALL AND WRITES THE TEXT FILES - DO THIS ONLY ONCE"""
    print()
    page = 0
    page_list =[]
    while True:
        request = requests.get(STEM + 'species/page/' + str(page) + TOKEN)
        response = request.json()
        filename = 'globalSpeciesPage' + str(page)
        # print('page', page, response['count'])
        if response['count'] == 0:
            break
        page_list.append(filename + '.txt')
        writeTXTFile(filename, response)
        page += 1

    #LOADS FROM EXISTING JSON TEXT FILES AND EXTENDS LIST 'result'
    result = []
    for p in page_list:
        with open(p, 'r') as f:
            contents = json.load(f)
            result.extend(contents['result'])
            f.close()

    #WRITES THE CONCATENATED 'result' LIST OF DICTS TO CSV
    writeCSVFile('globalSpeciesAssessment', result)

    page_list.append('globalSpeciesAssessment.csv')

    print('\nfiles in dir for global species assessment:')
    for p in page_list:
        print(' - ', p)


#THESE FUNCTIONS ARE GENERIC -------------------------------------------

def writeTXTFile(filename, response):
    """GENERIC CODE TO WRITE TXT FILE FROM 'response' """
    with open(filename + '.txt', 'w') as f:
        json.dump(response, f)
        f.close()
    print('Made', filename + '.txt')


def writeCSVFile(filename, result):
    """GENERIC CODE TO WRITE CSV FILE FROM PARSED 'result' """
    with open(filename + '.csv', 'w', newline='') as f:
        fieldnames = result[0].keys()
        write = csv.DictWriter(f, fieldnames=fieldnames)
        write.writeheader()
        count = 0
        for entry in result:
            write.writerow(entry)
            count += 1
        f.close()
    print('Made', filename + '.csv with', count, 'species')


def main():
    #THESE ARE CONSTANTS
    STEM = 'https://apiv3.iucnredlist.org/api/v3/'

    with open('token.txt', 'r') as t:
        TOKEN = t.read()
        t.close()

    COUNTRIES = ['CD', 'CG', 'GA', 'CM']
    rank_names = ['MAMMALIA', 'AVES', 'REPTILIA', 'AMPHIBIA']
    hab_list = ['scientific_name', 'taxonid', 'country', '1 - Forest', '1.1 - Forest - Boreal', '1.2 - Forest - Subarctic', '1.3 - Forest - Subantarctic', '1.4 - Forest - Temperate', '1.5 - Forest - Subtropical/Tropical Dry', '1.6 - Forest - Subtropical/Tropical Moist Lowland', '1.7 - Forest - Subtropical/Tropical Mangrove Vegetation Above High Tide Level', '1.8 - Forest - Subtropical/Tropical Swamp', '1.9 - Forest - Subtropical/Tropical Moist Montane', '2 - Savanna', '2.1 - Savanna - Dry', '2.2 - Savanna - Moist', '3 - Shrubland', '3.1 - Shrubland - Subarctic', '3.2 - Shrubland - Subantarctic', '3.3 - Shrubland - Boreal', '3.4 - Shrubland - Temperate', '3.5 - Shrubland - Subtropical/Tropical Dry', '3.6 - Shrubland - Subtropical/Tropical Moist', '3.7 - Shrubland - Subtropical/Tropical High Altitude', '3.8 - Shrubland - Mediterranean-type Shrubby Vegetation', '4 - Grassland', '4.1 - Grassland - Tundra', '4.2 - Grassland - Subarctic', '4.3 - Grassland - Subantarctic', '4.4 - Grassland - Temperate', '4.5 - Grassland - Subtropical/Tropical Dry', '4.6 - Grassland - Subtropical/Tropical Seasonally Wet/Flooded', '4.7 - Grassland - Subtropical/Tropical High Altitude', '5 - Wetlands (inland)', '5.1 - Wetlands (inland) - Permanent Rivers/Streams/Creeks (includes waterfalls)', '5.2 - Wetlands (inland) - Seasonal/Intermittent/Irregular Rivers/Streams/Creeks', '5.3 - Wetlands (inland) - Shrub Dominated Wetlands', '5.4 - Wetlands (inland) - Bogs, Marshes, Swamps, Fens, Peatlands', '5.5 - Wetlands (inland) - Permanent Freshwater Lakes (over 8ha)', '5.6 - Wetlands (inland) - Seasonal/Intermittent Freshwater Lakes (over 8ha)', '5.7 - Wetlands (inland) - Permanent Freshwater Marshes/Pools (under 8ha)', '5.8 - Wetlands (inland) - Seasonal/Intermittent Freshwater Marshes/Pools (under 8ha)', '5.9 - Wetlands (inland) - Freshwater Springs and Oases', '5.1 - Wetlands (inland) - Tundra Wetlands (incl. pools and temporary waters from snowmelt)', '5.11 - Wetlands (inland) - Alpine Wetlands (includes temporary waters from snowmelt)', '5.12 - Wetlands (inland) - Geothermal Wetlands', '5.13 - Wetlands (inland) - Permanent Inland Deltas', '5.14 - Wetlands (inland) - Permanent Saline, Brackish or Alkaline Lakes', '5.15 - Wetlands (inland) - Seasonal/Intermittent Saline, Brackish or Alkaline Lakes and Flats', '5.16 - Wetlands (inland) - Permanent Saline, Brackish or Alkaline Marshes/Pools', '5.17 - Wetlands (inland) - Seasonal/Intermittent Saline, Brackish or Alkaline Marshes/Pools', '5.18 - Wetlands (inland) - Karst and Other Subterranean Hydrological Systems (inland)', '6 - Rocky areas (eg. inland cliffs, mountain peaks)', '7 - Caves and Subterranean Habitats (non-aquatic)', '7.1 - Caves and Subterranean Habitats (non-aquatic) - Caves', '7.2 - Caves and Subterranean Habitats (non-aquatic) - Other Subterranean Habitats', '8 - Desert', '8.1 - Desert - Hot', '8.2 - Desert - Temperate', '8.3 - Desert - Cold', '9 - Marine Neritic', '9.1 - Marine Neritic - Pelagic', '9.2 - Marine Neritic - Subtidal Rock and Rocky Reefs', '9.3 - Marine Neritic - Subtidal Loose Rock/pebble/gravel', '9.4 - Marine Neritic - Subtidal Sandy', '9.5 - Marine Neritic - Subtidal Sandy-Mud', '9.6 - Marine Neritic - Subtidal Muddy', '9.7 - Marine Neritic - Macroalgal/Kelp', '9.8 - Marine Neritic - Coral Reef', '9.9 - Marine Neritic - Seagrass (Submerged)', '9.1 - Marine Neritic - Estuaries', '10 - Marine Oceanic', '10.1 - Marine Oceanic - Epipelagic (0-200m)', '10.2 - Marine Oceanic - Mesopelagic (200-1000m)', '10.3 - Marine Oceanic - Bathypelagic (1000-4000m)', '10.4 - Marine Oceanic - Abyssopelagic (4000-6000m)', '11 - Marine Deep Benthic', '11.1 - Marine Deep Benthic - Continental Slope/Bathyl Zone (200-4,000m)', '11.2 - Marine Deep Benthic - Abyssal Plain (4,000-6,000m)', '11.3 - Marine Deep Benthic - Abyssal Mountain/Hills (4,000-6,000m) 11.4 Marine Deep Benthic - Hadal/Deep Sea Trench (>6,000m)', '11.5 - Marine Deep Benthic - Seamount', '11.6 - Marine Deep Benthic - Deep Sea Vents (Rifts/Seeps)', '12 - Marine Intertidal', '12.1 - Marine Intertidal - Rocky Shoreline', '12.2 - Marine Intertidal - Sandy Shoreline and/or Beaches, Sand Bars, Spits, Etc', '12.3 - Marine Intertidal - Shingle and/or Pebble Shoreline and/or Beaches', '12.4 - Marine Intertidal - Mud Flats and Salt Flats', '12.5 - Marine Intertidal - Salt Marshes (Emergent Grasses)', '12.6 - Marine Intertidal - Tidepools', '12.7 - Marine Intertidal - Mangrove Submerged Roots', '13 - Marine Coastal/Supratidal', '13.1 - Marine Coastal/Supratidal - Sea Cliffs and Rocky Offshore Islands', '13.2 - Marine Coastal/supratidal - Coastal Caves/Karst', '13.3 - Marine Coastal/Supratidal - Coastal Sand Dunes', '13.4 - Marine Coastal/Supratidal - Coastal Brackish/Saline Lagoons/Marine Lakes', '13.5 - Marine Coastal/Supratidal - Coastal Freshwater Lakes', '14 - Artificial/Terrestrial', '14.1 - Artificial/Terrestrial - Arable Land', '14.2 - Artificial/Terrestrial - Pastureland', '14.3 - Artificial/Terrestrial - Plantations', '14.4 - Artificial/Terrestrial - Rural Gardens', '14.5 - Artificial/Terrestrial - Urban Areas', '14.6 - Artificial/Terrestrial - Subtropical/Tropical Heavily Degraded Former Forest', '15 - Artificial/Aquatic & Marine', '15.1 - Artificial/Aquatic - Water Storage Areas (over 8ha)', '15.2 - Artificial/Aquatic - Ponds (below 8ha)', '15.3 - Artificial/Aquatic - Aquaculture Ponds', '15.4 - Artificial/Aquatic - Salt Exploitation Sites', '15.5 - Artificial/Aquatic - Excavations (open)', '15.6 - Artificial/Aquatic - Wastewater Treatment Areas', '15.7 - Artificial/Aquatic - Irrigated Land (includes irrigation channels)', '15.8 - Artificial/Aquatic - Seasonally Flooded Agricultural Land', '15.9 - Artificial/Aquatic - Canals and Drainage Channels, Ditches', '15.1 - Artificial/Aquatic - Karst and Other Subterranean Hydrological Systems (human-made)', '15.11 - Artificial/Marine - Marine Anthropogenic Structures', '15.12 - Artificial/Marine - Mariculture Cages', '15.13 - Artificial/Marine - Mari/Brackishculture Ponds', '16 - Introduced vegetation', '17 - Other', '18 - Unknown']

    #TEST SMALL CHANGE FOR GIT

    #API CALLS------------------------------
    
    #GETS GLOBAL SPECIES ASSESSMENT
    # makeGlobSpAssesment(STEM, TOKEN)

    #GETS ALL SPECIES FOR A LIST OF COUNTRIES
    # allSpByCountries(STEM, TOKEN, COUNTRIES)
    
    #MAKES HABITATS CSV FROM LIST OF 'allSpByCountries()' CSVs
    # compileSpHabByCountries(STEM, TOKEN, hab_list)

    #NOT API CALLS--------------------------

    #GETS ALL SPECIES BELONGING TO ONE OR MORE TAXA OF THE SAME RANK
    # spFiltByTaxa(rank_names)

    #TAKES ALL SPECIES IN COUNTRY AND ALL SPECIES IN A TAXON AND RETURNS COMMON MEMBERS
    #EITHER ENTITY CAN BE A SINGLETON OR A LIST
    # getTaxaInCountries()

    #TAKES EXISTING LIST OF COUNTRIES AND FILTERS ALL SPECIES THAT EXIST IN GIVEN SUBHABITATS
    # spFiltByHabsInCountries(hab_list)


main()