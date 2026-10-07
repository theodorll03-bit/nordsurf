## Alle ruter i Open API, gruppert på tag

- **Ais** (15): `POST /api/ais_shipreg/statinfo/for-mmsis-time`, `POST /api/ais/positions/before-after`, `POST /api/ais/positions/for-mmsi-date`, `POST /api/ais/positions/for-mmsis-time`, `POST /api/ais/positions/within-bbox-time`, `POST /api/ais/positions/within-geom-time`, `POST /api/ais/sailed-distance/admin/dates`, `POST /api/ais/sailed-distance/fvpomr`, `POST /api/ais/sailed-distance/grunnlinje`, `POST /api/ais/sailed-distance/municipality`, `POST /api/ais/sailed-distance/municipality-fairway`, `POST /api/ais/sailed-distance/svoomr`, `POST /api/ais/statinfo/for-mmsis-time`, `POST /api/ais/statinfo/ships/free-text-time`, `POST /api/ais/yearly-stats/{fromYear}/{toYear}`
- **AisRealTime** (2): `GET /api/ais/realtime/geojson`, `GET /api/ais/realtime/vessels-by-type`
- **AisStatic** (1): `GET /api/ais/static-messages`
- **Anchorage** (7): `POST /api/anchorage/anchorage/by-dokid-dokstatus`, `POST /api/anchorage/anchorage/for-sysid-time`, `POST /api/anchorage/area/geojson`, `POST /api/anchorage/area/geojson/by-dokid-dokstatus`, `GET /api/anchorage/areas`, `POST /api/anchorage/duration-by-year-and-id`, `POST /api/anchorage/for-location-time2`
- **Auth** (10): `POST /api/auth/federated-login`, `POST /api/auth/identities/link`, `POST /api/auth/login`, `GET /api/auth/roles`, `POST /api/auth/roles`, `DELETE /api/auth/roles/{roleName}`, `GET /api/auth/users`, `GET /api/auth/users/{id}`, `POST /api/auth/users/{id}/roles`, `DELETE /api/auth/users/{id}/roles/{roleName}`
- **Bunkers** (1): `POST /api/bunkers`
- **Incident** (2): `POST /api/kystinfo/norvts-incidents`, `POST /api/kystinfo/norvts-incidents-public`
- **Indicators** (2): `GET /api/voyage/infographics/arrivals-per-day`, `GET /api/voyage/infographics/cruises-per-day`
- **Location** (13): `GET /api/location/all`, `POST /api/location/all`, `POST /api/location/connections/for-locations`, `GET /api/location/counties`, `POST /api/location/counties`, `POST /api/location/for-locations`, `POST /api/location/free-text`, `GET /api/location/norway/all`, `GET /api/location/norway/all/geojson`, `POST /api/location/time-in-port`, `POST /api/location/time-in-port/all`, `POST /api/location/time-in-port/osps`, `POST /api/location/time-in-port/osps-yearly`
- **Map** (5): `GET /api/maps/fvpomr/list`, `GET /api/maps/kommune/geojson`, `GET /api/maps/kommune/list`, `GET /api/maps/kommune/wkt`, `GET /api/maps/svoomr/list`
- **MarTraf** (2): `POST /api/martraf-tracks/intersects-line`, `POST /api/martraf-tracks/within-geom-time`
- **MarU** (2): `GET /api/maru/sailed-distance/county-municipality/{fromYearMonth}/{toYearMonth}`, `GET /api/maru/sailed-distance/management-area/{fromYearMonth}/{toYearMonth}`
- **MyData** (10): `GET /api/mydata`, `POST /api/mydata`, `DELETE /api/mydata/erase-all`, `GET /api/mydata/export-all`, `POST /api/mydata/files/folder`, `POST /api/mydata/files/upload`, `GET /api/mydata/files/{uuid}/download`, `DELETE /api/mydata/{uuid}`, `GET /api/mydata/{uuid}`, `PATCH /api/mydata/{uuid}/rename`
- **Pilotage** (2): `POST /api/pilotage/aggregated/for-years`, `POST /api/pilotage/for-locations-years`
- **RasterFrequency** (4): `GET /api/raster-frequency/ext/mapserver`, `POST /api/raster-frequency/ext/raster/statistics`, `GET /api/raster-frequency/ext/sld`, `POST /api/raster-frequency/statistics/v2`
- **RealtimeTrack** (2): `POST /api/realtime-tracks/intersects-line`, `POST /api/realtime-tracks/within-geom-time`
- **Ship** (20): `GET /api/ship/builtbetween/{fromYear}/{toYear}`, `GET /api/ship/combined/callsign/{callsign}`, `GET /api/ship/combined/callsign/{version}/{callsign}`, `GET /api/ship/combined/free-text`, `POST /api/ship/combined/free-text`, `GET /api/ship/combined/imo/{imo}`, `GET /api/ship/combined/imo/{version}/{imo}`, `GET /api/ship/combined/mmsi/{mmsi}`, `GET /api/ship/combined/mmsi/{version}/{mmsi}`, `POST /api/ship/combined/{version}/free-text`, `POST /api/ship/data/ais/for-mmsis-imos`, `GET /api/ship/data/ais/free-text`, `POST /api/ship/data/combined/for-mmsis-imos`, `POST /api/ship/data/fairplay/for-mmsis-imos`, `POST /api/ship/data/nsr/for-mmsis-imos`, `POST /api/ship/data/shipinfo/for-mmsis-imos`, `POST /api/ship/for-mmsis`, `POST /api/ship/free-text`, `GET /api/ship/nsr/download`, `GET /api/ship/shiptypes`
- **ShipDimensions** (3): `GET /api/ship-dimensions`, `POST /api/ship-dimensions`, `DELETE /api/ship-dimensions/{id}`
- **ShipType** (13): `GET /api/ship-type/statcode5/download`, `GET /api/vocabulary`, `GET /api/vocabulary/mapping`, `DELETE /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}`, `GET /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}`, `POST /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}`, `POST /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}/create`, `POST /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}/refresh`, `DELETE /api/vocabulary/terms/{vocabularyCode}`, `GET /api/vocabulary/terms/{vocabularyCode}`, `POST /api/vocabulary/terms/{vocabularyCode}`, `DELETE /api/vocabulary/terms/{vocabularyCode}/{term}`, `DELETE /api/vocabulary/{vocabularyCode}`
- **Shorepower** (1): `GET /api/shorepower/geojson`
- **Track** (17): `POST /api/tracks/async/download/by-voyage-timespan`, `POST /api/tracks/for-ships/by-mmsi`, `POST /api/tracks/for-ships/by-mmsi-mid`, `POST /api/tracks/for-ships/by-shipid`, `POST /api/tracks/frequency-counts`, `POST /api/tracks/frequency-counts/weekly`, `GET /api/tracks/get-passlines`, `POST /api/tracks/get-passlines`, `POST /api/tracks/intersects-line`, `POST /api/tracks/intersects-two-lines`, `POST /api/tracks/sailed-distance/for-ships/by-callsign`, `POST /api/tracks/sailed-distance/for-ships/by-imo`, `POST /api/tracks/sailed-distance/for-ships/by-mmsi`, `POST /api/tracks/speed/for-ships/by-callsign`, `POST /api/tracks/within-area`, `POST /api/tracks/within-area/by-mmsi`, `POST /api/tracks/within-municipality`
- **Voyage** (21): `POST /api/voyage/aggregated/arrivals`, `POST /api/voyage/aggregated/arrivals-by-day`, `POST /api/voyage/aggregated/cruise/public`, `POST /api/voyage/aggregated/departures-by-day`, `GET /api/voyage/aggregated/{fromYear}/{toYear}`, `POST /api/voyage/aggregated/{fromYear}/{toYear}`, `GET /api/voyage/arrivals-current-month-by-departure-country`, `POST /api/voyage/arrivals-departures/for-location`, `GET /api/voyage/arrivals-previous-month-by-departure-country`, `POST /api/voyage/arrivals/for-locations`, `GET /api/voyage/between/{fromDate}/{toDate}`, `GET /api/voyage/cruise/year-on-year-difference`, `GET /api/voyage/dangerous-goods/by-voyage-segments/{fromTime}/{toTime}`, `POST /api/voyage/departures/for-locations`, `POST /api/voyage/for-ships/by-callsign`, `POST /api/voyage/for-ships/by-mmsi`, `POST /api/voyage/for-ships/by-shipid`, `GET /api/voyage/international-detail/{fromTime}/{toTime}`, `GET /api/voyage/international/{from_date}/{to_date}`, `POST /api/voyage/passengers/by-date-location`, `GET /api/voyage/passengers/by-voyage-segments/{fromTime}/{toTime}`

## Oppslag på KystVær-datasettet (gjettede ruter)

- https://kystdatahuset.no/ws/api/dataset/d7f12c93-d761-42fe-8370-3f5a5a747f63: 404  0 tegn ``
- https://kystdatahuset.no/ws/api/datasets/d7f12c93-d761-42fe-8370-3f5a5a747f63: 404  0 tegn ``
- https://kystdatahuset.no/ws/api/catalog/dataset/d7f12c93-d761-42fe-8370-3f5a5a747f63: 404  0 tegn ``
- https://kystdatahuset.no/ws/api/metadata/d7f12c93-d761-42fe-8370-3f5a5a747f63: 404  0 tegn ``
- https://kystdatahuset.no/api/dataset/d7f12c93-d761-42fe-8370-3f5a5a747f63: 200 text/html 3535 tegn `<!DOCTYPE html><html lang="nb"><head> <meta charset="utf-8"> <meta name="viewport" content="width=device-width, initial-scale=1"> <meta name="theme-color" content="#F9F6F3"> <meta name="description" c`
- https://kystdatahuset.kystverket.no/ws/api/dataset/d7f12c93-d761-42fe-8370-3f5a5a747f63: 404  0 tegn ``

## Lenkehøsting fra Kystdatahuset/Kystverket-sidene

- https://kystdatahuset.no/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/artikkel/api-tilgang: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/datasett: status 200, 3374 tegn, 2 relevante lenker: ['/api-access', 'https://kystdatahuset.no/datasett']
- https://kystdatahuset.no/data: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/api: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/artikkel: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://www.kystverket.no/sjovegen/vartjenester/kystvar/: status 200, 48933 tegn, 28 relevante lenker: ['/klima-og-barekraft/kystverkets-klimaregnskap/', '/kystkultur/fyrstasjoner/', '/kystkultur/kystverkets-historie/', '/kystkultur/kystverkmusea/', '/nyheter/2024/kystverket-setter-kurs-og-kutter-egne-klimagassutslipp/', '/om-kystverket/', '/om-kystverket/arrangementer/', '/om-kystverket/barentswatch/', '/om-kystverket/hva-gjor-kystverket/', '/om-kystverket/jobb-i-kystverket/', '/om-kystverket/kunnskapsdatabasen/', '/om-kystverket/kystverket-samfunnsoppdrag/', '/om-kystverket/kystverkets-personvernerklaring/', '/om-kystverket/nasjonal-transportplan/', '/om-kystverket/profilhandbok/', '/sjovegen/kystverkets-fartoyer/', '/sjovegen/vartjenester/kystvar/', '/varsle-oss/defekte-ais--og-dgps-stasjoner/', 'https://apps.apple.com/no/app/kystv%C3%A6r-kystverket/id698101935?l=nb', 'https://kystdatahuset.no/detail/dataset/d7f12c93-d761-42fe-8370-3f5a5a747f63', 'https://nais.kystverket.no/', 'https://play.google.com/store/apps/details?id=no.scanmatic.kystverketapp&amp;hl=no&amp;gl=US', 'https://selvbetjening.kystverket.no/nb-NO', 'https://www.facebook.com/Kystverket/', 'https://www.instagram.com/kystverket/', 'https://www.kystverket.no/sjovegen/vartjenester/kystvar/', 'mailto:harald.aasheim@kystverket.no', 'mailto:post@kystverket.no']
- https://www.kystverket.no/nyheter/2024/kystvar-varsensor-malinger-for-sjofarende/: status 200, 48358 tegn, 26 relevante lenker: ['/klima-og-barekraft/kystverkets-klimaregnskap/', '/kystkultur/fyrstasjoner/', '/kystkultur/kystverkets-historie/', '/kystkultur/kystverkmusea/', '/nyheter/2024/kystvar-varsensor-malinger-for-sjofarende/', '/nyheter/2024/kystverket-setter-kurs-og-kutter-egne-klimagassutslipp/', '/om-kystverket/', '/om-kystverket/arrangementer/', '/om-kystverket/barentswatch/', '/om-kystverket/hva-gjor-kystverket/', '/om-kystverket/jobb-i-kystverket/', '/om-kystverket/kunnskapsdatabasen/', '/om-kystverket/kystverket-samfunnsoppdrag/', '/om-kystverket/kystverkets-personvernerklaring/', '/om-kystverket/nasjonal-transportplan/', '/om-kystverket/profilhandbok/', '/sjovegen/kystverkets-fartoyer/', '/sjovegen/vartjenester/kystvar/', '/varsle-oss/defekte-ais--og-dgps-stasjoner/', 'https://nais.kystverket.no/', 'https://selvbetjening.kystverket.no/nb-NO', 'https://www.facebook.com/Kystverket/', 'https://www.instagram.com/kystverket/', 'https://www.kystverket.no/navigasjonstjenester/kystvar/', 'https://www.kystverket.no/nyheter/2024/kystvar-varsensor-malinger-for-sjofarende/', 'mailto:post@kystverket.no']
- https://kystdatahuset.no/api-access: status 200, 3440 tegn, 2 relevante lenker: ['/api-access', 'https://kystdatahuset.no/api-access']
- https://kystdatahuset.no/klima-og-barekraft/kystverkets-klimaregnskap/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/kystkultur/fyrstasjoner/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/kystkultur/kystverkets-historie/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/kystkultur/kystverkmusea/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/nyheter/2024/kystverket-setter-kurs-og-kutter-egne-klimagassutslipp/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/arrangementer/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/barentswatch/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/hva-gjor-kystverket/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/jobb-i-kystverket/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/kunnskapsdatabasen/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/kystverket-samfunnsoppdrag/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/kystverkets-personvernerklaring/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/nasjonal-transportplan/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/om-kystverket/profilhandbok/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/sjovegen/kystverkets-fartoyer/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/sjovegen/vartjenester/kystvar/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/varsle-oss/defekte-ais--og-dgps-stasjoner/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/detail/dataset/d7f12c93-d761-42fe-8370-3f5a5a747f63: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']
- https://kystdatahuset.no/nyheter/2024/kystvar-varsensor-malinger-for-sjofarende/: status 200, 3535 tegn, 1 relevante lenker: ['/api-access']

## Swagger: vær/vind-ruter i Kystdatahuset Open API

- servers: [{'url': '/ws'}], global security: None, securitySchemes: ['JWT Bearer']
- antall ruter totalt: 142
- ruter som matcher vær/vind-nøkkelord: 18
### POST /api/ais/yearly-stats/{fromYear}/{toYear}
- tags ['Ais'], summary: Load annual message statistics for Kystverkets AIS database
- parametre: [('fromYear', 'path', True, 'integer'), ('toYear', 'path', True, 'integer')], body: nei, security: arver global
### POST /api/auth/federated-login
- tags ['Auth'], summary: Login with a token issued by a federated identity provider for Kystverket-internal employees
to retrieve a JWT-token for consequtive requests.
- parametre: [], body: ja, security: arver global
### GET /api/auth/roles
- tags ['Auth'], summary: List all roles. Kystverket-internal only. (Auth)
- parametre: [], body: nei, security: [{'JWT Bearer': [None]}]
- GET uten parametre: status 401, , 0 tegn: ``
### POST /api/auth/roles
- tags ['Auth'], summary: Create a role, or update its description if it already exists. Kystverket-internal only. (Auth)
- parametre: [], body: ja, security: [{'JWT Bearer': [None]}]
### GET /api/auth/users
- tags ['Auth'], summary: Search users by email or display name. Kystverket-internal only. (Auth)
- parametre: [('query', 'query', None, 'string'), ('limit', 'query', None, 'integer'), ('offset', 'query', None, 'integer')], body: nei, security: [{'JWT Bearer': [None]}]
- GET uten parametre: status 401, , 0 tegn: ``
### GET /api/auth/users/{id}
- tags ['Auth'], summary: Get a single user along with their assigned roles. Kystverket-internal only. (Auth)
- parametre: [('id', 'path', True, 'string')], body: nei, security: [{'JWT Bearer': [None]}]
### POST /api/auth/users/{id}/roles
- tags ['Auth'], summary: Assign a role (creating it if it doesn't already exist) to a user. Kystverket-internal only. (Auth)
- parametre: [('id', 'path', True, 'string')], body: ja, security: [{'JWT Bearer': [None]}]
### GET /api/ship-type/statcode5/download
- tags ['ShipType'], summary: Retrieve all Statcode5 code list with all attributes (Auth)
- parametre: [], body: nei, security: [{'JWT Bearer': [None]}]
- GET uten parametre: status 401, , 0 tegn: ``
### POST /api/ship/data/fairplay/for-mmsis-imos
- tags ['Ship'], summary: Get information about ships from Fairplay (Auth)
- parametre: [], body: ja, security: [{'JWT Bearer': [None]}]
### POST /api/ship/data/shipinfo/for-mmsis-imos
- tags ['Ship'], summary: Get information about ships from Shipinfo
- parametre: [], body: ja, security: arver global
### GET /api/ship/nsr/download
- tags ['Ship'], summary: This *restricted* web service allows you to download the entire NewShipRep ship registry (Auth)
- parametre: [], body: nei, security: [{'JWT Bearer': [None]}]
- GET uten parametre: status 401, , 0 tegn: ``
### GET /api/vocabulary/mapping
- tags ['ShipType'], summary: Retrieve all ship type mappings between source and target vocabularies (Auth)
- parametre: [], body: nei, security: [{'JWT Bearer': [None]}]
- GET uten parametre: status 401, , 0 tegn: ``
### GET /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}
- tags ['ShipType'], summary: Retrieve all ship type mappings between source and target vocabularies (Auth)
- parametre: [('fromVocabularyCode', 'path', True, 'string'), ('toVocabularyCode', 'path', True, 'string')], body: nei, security: [{'JWT Bearer': [None]}]
### POST /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}
- tags ['ShipType'], summary: Upload one or more ship type mappings between two existing vocabularies
If the mapping already exists, it will be updated with the new information.
I.e. if the source vocabulary and source id alread
- parametre: [('fromVocabularyCode', 'path', True, 'string'), ('toVocabularyCode', 'path', True, 'string')], body: ja, security: [{'JWT Bearer': [None]}]
### POST /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}/create
- tags ['ShipType'], summary: Create (or re-create) the materialized view used to look up mappings
between two vocabularies. (Auth)
- parametre: [('fromVocabularyCode', 'path', True, 'string'), ('toVocabularyCode', 'path', True, 'string')], body: nei, security: [{'JWT Bearer': [None]}]
### POST /api/vocabulary/mapping/{fromVocabularyCode}/{toVocabularyCode}/refresh
- tags ['ShipType'], summary: Refresh the materialized view used to look up mappings between two vocabularies. (Auth)
- parametre: [('fromVocabularyCode', 'path', True, 'string'), ('toVocabularyCode', 'path', True, 'string')], body: nei, security: [{'JWT Bearer': [None]}]
### GET /api/vocabulary/terms/{vocabularyCode}
- tags ['ShipType'], summary: Get the terms from a vocabulary. (Auth)
- parametre: [('vocabularyCode', 'path', True, 'string')], body: nei, security: [{'JWT Bearer': [None]}]
### POST /api/vocabulary/terms/{vocabularyCode}
- tags ['ShipType'], summary: Upsert one or more terms to an existing vocabulary.
If the term already exists, it will be updated with the new information. (Auth)
- parametre: [('vocabularyCode', 'path', True, 'string')], body: ja, security: [{'JWT Bearer': [None]}]

# KystVær/Kystdatahuset-sondering, 2026-10-07 16:04 UTC

## https://kystdatahuset.no/ws/swagger/index.html
- status 200, text/html;charset=utf-8, 6879 tegn, endte på https://kystdatahuset.kystverket.no/ws/swagger/index.html, nøkkel/innlogging antydet: nei
- lenker/nøkler: ['./swagger-ui.css']
- utdrag: `<!-- HTML for static distribution bundle build --> <!DOCTYPE html> <html lang="en"> <head> <meta charset="UTF-8"> <title>Swagger UI</title> <link rel="stylesheet" type="text/css" href="./swagger-ui.css"> <link rel="icon" type="image/png" href="./favicon-32x32.png" sizes="32x32" /> <link rel="icon" type="image/png" href="./favicon-16x16.png" sizes="16x16" /> <style> html { box-sizing: border-box; o`

## https://kystdatahuset.no/ws/swagger/v1/swagger.json
- status 200, application/json;charset=utf-8, 526856 tegn, endte på https://kystdatahuset.kystverket.no/ws/swagger/v1/swagger.json, nøkkel/innlogging antydet: nei
- lenker/nøkler: ["paths: ['/api/ais_shipreg/statinfo/for-mmsis-time', '/api/ais/positions/before-after', '/api/ais/positions/for-mmsi-date', '/api/ais/positions/for-mmsis-time', '/api/ais/positions/within-bbox-time', '/api/ais/positions/within-geom-time', '/api/ais/realtime/geojson', '/api/ais/realtime/vessels-by-type', '/api/ais/sailed-distance/admin/dates', '/api/ais/sailed-distance/fvpomr', '/api/ais/sailed-distance/grunnlinje', '/api/ais/sailed-distance/municipality', '/api/ais/sailed-distance/municipality-fairway', '/api/ais/sailed-distance/svoomr', '/api/ais/static-messages', '/api/ais/statinfo/for-mmsis-time', '/api/ais/statinfo/ships/free-text-time', '/api/ais/yearly-stats/{fromYear}/{toYear}', '/api/anchorage/anchorage/by-dokid-dokstatus', '/api/anchorage/anchorage/for-sysid-time', '/api/anchorage/area/geojson', '/api/anchorage/area/geojson/by-dokid-dokstatus', '/api/anchorage/areas', '/api/anchorage/duration-by-year-and-id', '/api/anchorage/for-location-time2', '/api/auth/federated-login', '/api/auth/identities/link', '/api/auth/login', '/api/auth/roles', '/api/auth/roles/{roleName}', '/api/auth/users', '/api/auth/users/{id}', '/api/auth/users/{id}/roles', '/api/auth/users/{id}/roles/{roleName}', '/api/bunkers', '/api/kystinfo/norvts-incidents', '/api/kystinfo/norvts-incidents-public', '/api/location/all', '/api/location/connections/for-locations', '/api/location/counties', '/api/location/for-locations', '/api/location/free-text', '/api/location/norway/all', '/api/location/norway/all/geojson', '/api/location/time-in-port', '/api/location/time-in-port/all', '/api/location/time-in-port/osps', '/api/location/time-in-port/osps-yearly', '/api/maps/fvpomr/list', '/api/maps/kommune/geojson', '/api/maps/kommune/list', '/api/maps/kommune/wkt', '/api/maps/svoomr/list', '/api/martraf-tracks/intersects-line', '/api/martraf-tracks/within-geom-time', '/api/maru/sailed-distance/county-municipality/{fromYearMonth}/{toYearMonth}', '/api/maru/sailed-distance/management-area/{fromYearMonth}/{toYearMonth}', '/api/mydata', '/api/mydata/erase-all', '/api/mydata/export-all']"]
- utdrag: `{ "openapi": "3.0.1", "info": { "title": "Kystdatahuset Open API", "description": "Web Service API for open and authorized access to data from the Norwegian Coastal Administration (Kystverket).", "termsOfService": "https://kystdatahuset.no/artikkel/api-tilgang", "contact": { "name": "The Norwegian Coastal Administration (Kystverket)", "url": "https://kystverket.no", "email": "support.kystdatahuset`

## https://kystdatahuset.no/ws/swagger.json
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/swagger.json, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/swagger.json
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/swagger.json, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/vaer
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/vaer, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/vaer/stasjoner
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/vaer/stasjoner, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/vaer/stations
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/vaer/stations, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/kystvaer
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/kystvaer, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/kystvaer/stations
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/kystvaer/stations, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/kystvaer/stasjoner
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/kystvaer/stasjoner, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/weather/stations
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/weather/stations, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystdatahuset.no/ws/api/wind/stations
- status 404, application/problem+json, 162 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/wind/stations, nøkkel/innlogging antydet: nei
- lenker/nøkler: ["keys: ['type', 'title', 'status', 'traceId']"]
- utdrag: `{"type":"https://tools.ietf.org/html/rfc9110#section-15.5.5","title":"Not Found","status":404,"traceId":"00-ba76b2adf7eef612ec20c0c4e6968b66-7308489d42846b6e-00"}`

## https://kystdatahuset.no/ws/api/windstations
- status 404, , 0 tegn, endte på https://kystdatahuset.kystverket.no/ws/api/windstations, nøkkel/innlogging antydet: nei
- utdrag: ``

## https://kystvaer.kystverket.no/
- FEIL: HTTPSConnectionPool(host='kystvaer.kystverket.no', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='kystvaer.ky

## https://kystvaer.kystverket.no/api/
- FEIL: HTTPSConnectionPool(host='kystvaer.kystverket.no', port=443): Max retries exceeded with url: /api/ (Caused by NameResolutionError("HTTPSConnection(host='kystvae

## https://kystvaer.kystverket.no/api/stations
- FEIL: HTTPSConnectionPool(host='kystvaer.kystverket.no', port=443): Max retries exceeded with url: /api/stations (Caused by NameResolutionError("HTTPSConnection(host=

## https://kystvaer.kystverket.no/api/v1/stations
- FEIL: HTTPSConnectionPool(host='kystvaer.kystverket.no', port=443): Max retries exceeded with url: /api/v1/stations (Caused by NameResolutionError("HTTPSConnection(ho

## https://kystvaer.kystverket.no/api/observations
- FEIL: HTTPSConnectionPool(host='kystvaer.kystverket.no', port=443): Max retries exceeded with url: /api/observations (Caused by NameResolutionError("HTTPSConnection(h

## https://kystvar.kystverket.no/
- FEIL: HTTPSConnectionPool(host='kystvar.kystverket.no', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='kystvar.kyst

## https://www.kystverket.no/sjovegen/vartjenester/kystvar/
- status 200, text/html; charset=utf-8, 48933 tegn, endte på https://www.kystverket.no/sjovegen/vartjenester/kystvar/, nøkkel/innlogging antydet: nei
- lenker/nøkler: ['https://www.kystverket.no/sjovegen/vartjenester/kystvar/', '/varsle-oss/defekte-ais--og-dgps-stasjoner/', 'https://selvbetjening.kystverket.no/nb-NO', '/varsle-oss/defekte-ais--og-dgps-stasjoner/', 'https://selvbetjening.kystverket.no/nb-NO', 'https://nais.kystverket.no/', '/sjovegen/kystverkets-fartoyer/', '/kystkultur/fyrstasjoner/', '/kystkultur/kystverkets-historie/', '/kystkultur/kystverkmusea/', '/nyheter/2024/kystverket-setter-kurs-og-kutter-egne-klimagassutslipp/', '/klima-og-barekraft/kystverkets-klimaregnskap/', '/om-kystverket/', '/om-kystverket/kystverket-samfunnsoppdrag/', '/om-kystverket/profilhandbok/', '/om-kystverket/jobb-i-kystverket/', '/om-kystverket/nasjonal-transportplan/', '/om-kystverket/hva-gjor-kystverket/', '/om-kystverket/arrangementer/', '/om-kystverket/barentswatch/', '/om-kystverket/kunnskapsdatabasen/', '/sjovegen/vartjenester/kystvar/', 'https://play.google.com/store/apps/details?id=no.scanmatic.kystverketapp&amp;hl=no&amp;gl=US', 'https://apps.apple.com/no/app/kystv%C3%A6r-kystverket/id698101935?l=nb', 'mailto:harald.aasheim@kystverket.no', 'mailto:post@kystverket.no', '/om-kystverket/kystverkets-personvernerklaring/', '/om-kystverket/jobb-i-kystverket/', 'https://www.facebook.com/Kystverket/', 'https://www.instagram.com/kystverket/']
- utdrag: `<!DOCTYPE html> <html lang="no" class="no-js"> <head prefix="og: https://ogp.me/ns# article: https://ogp.me/ns/article#"> <meta charset="utf-8" /> <meta content="width=device-width,initial-scale=1" name="viewport" /> <title>kystv&#xE6;r | Kystverket - tar ansvar for sj&#xF8;veien</title> <meta content="Last ned KystV&#xE6;r-appen og f&#xE5; n&#xF8;yaktige og oppdaterte vindm&#xE5;linger for 120 ut`

## https://kystinfo.no/
- status 200, text/html; charset=utf-8, 161244 tegn, endte på https://kystinfo.no/, nøkkel/innlogging antydet: nei
- utdrag: ` <!DOCTYPE html> <html xmlns="http://www.w3.org/1999/xhtml"> <head><meta charset="utf-8" /><title> Kystinfo.kystverket.no </title><meta property="og:type" content="website" /><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" /><meta name="apple-mobile-web-app-capable" content="yes" /><meta name="apple-mobile-web-app-status-bar-style" content`

## https://kystverket.avadaptive.no/api/core/swagger/index.html
- status 200, text/html;charset=utf-8, 1070 tegn, endte på https://kystverket.avadaptive.no/api/core/swagger/index.html, nøkkel/innlogging antydet: nei
- lenker/nøkler: ['./swagger-ui.css']
- utdrag: `<!-- HTML for static distribution bundle build --> <!DOCTYPE html> <html lang="en"> <head> <meta charset="UTF-8"> <title>Swagger UI</title> <link rel="stylesheet" type="text/css" href="./swagger-ui.css"> <link rel="stylesheet" type="text/css" href="./index.css"> <link rel="icon" type="image/png" href="./favicon-32x32.png" sizes="32x32" /> <link rel="icon" type="image/png" href="./favicon-16x16.png`

## https://kystverket.avadaptive.no/api/core/swagger/v1/swagger.json
- status 200, application/json;charset=utf-8, 893903 tegn, endte på https://kystverket.avadaptive.no/api/core/swagger/v1/swagger.json, nøkkel/innlogging antydet: nei
- lenker/nøkler: ["paths: ['/.well-known/oauth-authorization-server', '/.well-known/oauth-protected-resource/api/core/v1/mcp/data', '/debug/actors', '/debug/claims', '/debug/clienttoken', '/debug/elevated', '/debug/headers', '/debug/identity', '/debug/token', '/redirect/index', '/redirect/login', '/status', '/system/v1/migrations/{module}/{migration}/reset', '/system/v1/migrations/{module}/{migration}', '/system/v1/migrations/{module}', '/v1/adaptive3import/{id}/instancesetup/{key}', '/v1/adaptive3import/{id}/resources/{resourceId}/import/digiTheme', '/v1/adaptive3import/{id}/resources/{resourceId}/import/postgresTheme', '/v1/adaptive3import/{id}/resources/{resourceId}/import/themeDictionary', '/v1/adaptive3import/{id}/resources/{resourceId}/import/wmsTheme', '/v1/adaptive3import/{id}/resources', '/v1/adaptive3import/{id}/roles/{ident}', '/v1/adaptive3import/{id}/users', '/v1/applications/custom-apps/{type}', '/v1/applications/operations', '/v1/applications/schema', '/v1/applications/{ident}/operations', '/v1/applications/{ident}/permissions/grants', '/v1/applications/{ident}/permissions/me', '/v1/applications/{ident}/permissions/revoke', '/v1/applications/{ident}/permissions', '/v1/applications/{id}', '/v1/applications/{type}/{ident}/config', '/v1/applications/{type}/{ident}', '/v1/applications', '/v1/arcgisrest/info', '/v1/cadastre/access', '/v1/cadastre/geosearch', '/v1/cadastre/neighbors/{unitId}', '/v1/cadastre/parcel/{unitId}', '/v1/cadastre/search', '/v1/cadastre/status', '/v1/cadastre/unit/{unitId}', '/v1/cadastre/userinfo', '/v1/categories/operations', '/v1/categories/schema', '/v1/categories/tree', '/v1/categories/{ident}/config', '/v1/categories/{ident}/operations', '/v1/categories/{ident}/permissions/grants', '/v1/categories/{ident}/permissions/me', '/v1/categories/{ident}/permissions/revoke', '/v1/categories/{ident}/permissions', '/v1/categories/{ident}', '/v1/categories', '/v1/contentcollections/operations', '/v1/contentcollections/schema', '/v1/contentcollections/{ident}/config', '/v1/contentcollections/{ident}/operations', '/v1/contentcollections/{ident}/permissions/grants']"]
- utdrag: `{ "openapi": "3.0.4", "info": { "title": "CoreApi", "version": "1.0" }, "servers": [ { "url": "/api/core" } ], "paths": { "/.well-known/oauth-authorization-server": { "get": { "tags": [ "WellKnown" ], "parameters": [ { "name": "X-Gaia-Elevated", "in": "header", "description": "Set to true to use Administrator actor (you still need to be authorized).", "schema": { "type": "boolean", "default": fals`

## https://frost.met.no/sources/v0.jsonld?types=SensorSystem&country=NO&municipality=TROMS%C3%98
- status 401, text/plain; charset=UTF-8, 454 tegn, endte på https://frost.met.no/sources/v0.jsonld?types=SensorSystem&country=NO&municipality=TROMS%C3%98, nøkkel/innlogging antydet: ja
- utdrag: `{ "@context" : "https://frost.met.no/schema", "@type" : "ErrorResponse", "apiVersion" : "v0", "license" : "https://creativecommons.org/licenses/by/3.0/no/", "createdAt" : "2026-10-07T16:04:53Z", "queryTime" : 0, "currentLink" : "https://frost.met.no/sources/v0.jsonld?types=SensorSystem&country=NO&municipality=TROMS%C3%98", "error" : { "code" : 401, "message" : "Unauthorized", "reason" : "Missing a`

## https://frost.met.no/api.html
- status 200, text/html; charset=UTF-8, 7760 tegn, endte på https://frost.met.no/api.html, nøkkel/innlogging antydet: nei
- lenker/nøkler: ['/stylesheets/swagger_mod.css', '/api.html']
- utdrag: ` <!DOCTYPE html> <html lang="en"> <head> <!-- Basic Page Needs –––––––––––––––––––––––––––––––––––––––––––––––––– --> <meta charset="utf-8"> <title>Frost API</title> <meta name="description" content=""> <meta name="author" content=""> <!-- Mobile Specific Metas –––––––––––––––––––––––––––––––––––––––––––––––––– --> <meta name="viewport" content="width=device-width, initial-scale=1"> <!-- Favicon –`
