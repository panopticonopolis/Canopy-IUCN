# Canopy-IUCN

Querying and Analyzing the IUCN Red List

The main program is 'iucn.py', which performs a number of API-based and local queries to interrogate the IUCN Red List database, with a specific eye towards the four principal countries in which the Congo Basin rainforest is located: DRC, Congo, Gabon amd Cameroon.

The version of Python used is 3.7.1 and development was done in a MacOS environment. I haven't tested it for Windows compatibility, or for earlier versions of Python. For example, pre-3.7 versions of Python may not guarantee order of items in dictionaries, which may have unintended consequences here. 

Access to the IUCN API requires a token that is issued by that organization. See https://apiv3.iucnredlist.org/api/v3/docs for more details.
