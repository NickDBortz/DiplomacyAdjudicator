from player import Player
from territory import LandTerritory, WaterTerritory

def init_classic_map(map_object):
    # --- Russia ---
    russia = Player('Russia')
    # Finland
    finland = LandTerritory('Finland', 'FIN', is_supply_center=False, owner=russia)
    # St Petersburg * (North/South Coast)
    st_petersburg = LandTerritory('St Petersburg', 'STP', is_supply_center=True, owner=russia)
    # Livonia
    livonia = LandTerritory('Livonia', 'LIV', is_supply_center=False, owner=russia)
    # Moscow *
    moscow = LandTerritory('Moscow', 'MOS', is_supply_center=True, owner=russia)
    # Warsaw *
    warsaw = LandTerritory('Warsaw', 'WAR', is_supply_center=True, owner=russia)
    # Ukraine
    ukraine = LandTerritory('Ukraine', 'UKR', is_supply_center=False, owner=russia)
    # Sevastopol *
    sevastopol = LandTerritory('Sevastopol', 'SEV', is_supply_center=True, owner=russia)

    # --- England ---
    england = Player('England')
    # Edinburgh *
    edinburgh = LandTerritory('Edinburgh', 'EDI', is_supply_center=True, owner=england)
    # Yorkshire
    yorkshire = LandTerritory('Yorkshire', 'YOR', is_supply_center=False, owner=england)
    # London *
    london = LandTerritory('London', 'LON', is_supply_center=True, owner=england)
    # Wales
    wales = LandTerritory('Wales', 'WAL', is_supply_center=False, owner=england)
    # Liverpool *
    liverpool = LandTerritory('Liverpool', 'LVP', is_supply_center=True, owner=england)
    # Clyde
    clyde = LandTerritory('Clyde', 'CLY', is_supply_center=False, owner=england)

    # --- France ---
    france = Player('France')
    # Brest *
    brest = LandTerritory('Brest', 'BRE', is_supply_center=True, owner=france)
    # Picardy
    picardy = LandTerritory('Picardy', 'PIC', is_supply_center=False, owner=france)
    # Paris *
    paris = LandTerritory('Paris', 'PAR', is_supply_center=True, owner=france)
    # Burgundy
    burgundy = LandTerritory('Burgundy', 'BUR', is_supply_center=False, owner=france)
    # Gascony
    gascony = LandTerritory('Gascony', 'GAS', is_supply_center=False, owner=france)
    # Marseilles *
    marseilles = LandTerritory('Marseilles', 'MAR', is_supply_center=True, owner=france)

    # --- Italy ---
    italy = Player('Italy')
    # Piedmont
    piedmont = LandTerritory('Piedmont', 'PIE', is_supply_center=False, owner=italy)
    # Venice *
    venice = LandTerritory('Venice', 'VEN', is_supply_center=True, owner=italy)
    # Tuscany
    tuscany = LandTerritory('Tuscany', 'TUS', is_supply_center=False, owner=italy)
    # Rome *
    rome = LandTerritory('Rome', 'ROM', is_supply_center=True, owner=italy)
    # Naples *
    naples = LandTerritory('Naples', 'NAP', is_supply_center=True, owner=italy)
    # Apulia
    apulia = LandTerritory('Apulia', 'APU', is_supply_center=False, owner=italy)

    # --- Germany ---
    germany = Player('Germany')
    # Kiel *
    kiel = LandTerritory('Kiel', 'KIE', is_supply_center=True, owner=germany)
    # Berlin *
    berlin = LandTerritory('Berlin', 'BER', is_supply_center=True, owner=germany)
    # Prussia
    prussia = LandTerritory('Prussia', 'PRU', is_supply_center=False, owner=germany)
    # Ruhr
    ruhr = LandTerritory('Ruhr', 'RUH', is_supply_center=False, owner=germany)
    # Munich *
    munich = LandTerritory('Munich', 'MUN', is_supply_center=True, owner=germany)
    # Silesia
    silesia = LandTerritory('Silesia', 'SIL', is_supply_center=False, owner=germany)

    # --- Austria-Hungary ---
    austria_hungary = Player('Austria-Hungary')
    # Bohemia
    bohemia = LandTerritory('Bohemia', 'BOH', is_supply_center=False, owner=austria_hungary)
    # Galicia
    galicia = LandTerritory('Galicia', 'GAL', is_supply_center=False, owner=austria_hungary)
    # Vienna *
    vienna = LandTerritory('Vienna', 'VIE', is_supply_center=True, owner=austria_hungary)
    # Budapest *
    budapest = LandTerritory('Budapest', 'BUD', is_supply_center=True, owner=austria_hungary)
    # Tyrolia
    tyrolia = LandTerritory('tyrolia', 'TYR', is_supply_center=False, owner=austria_hungary)
    # Trieste *
    trieste = LandTerritory('Trieste', 'TRI', is_supply_center=True, owner=austria_hungary)

    # --- Turkey ---
    turkey = Player('Turkey')
    # Constantinople *
    constantinople = LandTerritory('Constantinople', 'CON', is_supply_center=True, owner=turkey)
    # Ankara *
    ankara = LandTerritory('Ankara', 'ANK', is_supply_center=True, owner=turkey)
    # Armenia
    armenia = LandTerritory('Armenia', 'ARM', is_supply_center=False, owner=turkey)
    # Smyrna *
    smyrna = LandTerritory('Smyrna', 'SMY', is_supply_center=True, owner=turkey)
    # Syria
    syria = LandTerritory('Syria', 'SYR', is_supply_center=False, owner=turkey)

    # --- Uncontrolled ---
    # Norway *
    norway = LandTerritory('Norway', 'NOR', is_supply_center=True, owner=None)
    # Sweden *
    sweden = LandTerritory('Sweden', 'SWE', is_supply_center=True, owner=None)
    # Denmark *
    denmark = LandTerritory('Denmark', 'DEN', is_supply_center=True, owner=None)
    # Holland *
    holland = LandTerritory('Holland', 'HOL', is_supply_center=True, owner=None)
    # Belgium *
    belgium = LandTerritory('Belgium', 'BEL', is_supply_center=True, owner=None)
    # Portugal *
    portugal = LandTerritory('Portugal', 'POR', is_supply_center=True, owner=None)
    # Spain * (North/South Coast)
    spain = LandTerritory('Spain', 'SPA', is_supply_center=True, owner=None)
    # North Africa
    north_africa = LandTerritory('North Africa', 'AFR', is_supply_center=False, owner=None)
    # Tunis *
    tunis = LandTerritory('Tunis', 'TUN', is_supply_center=True, owner=None)
    # Rumania *
    rumania = LandTerritory('Rumania', 'RUM', is_supply_center=True, owner=None)
    # Bulgaria * (North/South Coast)
    bulgaria = LandTerritory('Bulgaria', 'BUL', is_supply_center=True, owner=None)
    # Serbia *
    serbia = LandTerritory('Serbia', 'SER', is_supply_center=True, owner=None)
    # Albania
    albania = LandTerritory('Albania', 'ALB', is_supply_center=False, owner=None)
    # Greece *
    greece = LandTerritory('Greece', 'GRE', is_supply_center=True, owner=None)

    # --- Water ---
    # North Atlantic Ocean
    north_atlantic_ocean = WaterTerritory('North Atlantic Ocean', 'NAO', owner=None)
    # Norwegian Sea
    norwegian_sea = WaterTerritory('Norwegian Sea', 'NRG', owner=None)
    # Barents Sea
    barents_sea = WaterTerritory('Brents Sea', 'BAR', owner=None)
    # North Sea
    north_sea = WaterTerritory('North Sea', 'NTH', owner=None)
    # Gulf of Bothnia
    gulf_of_bothnia = WaterTerritory('Gulf of Bothnia', 'GOB', owner=None)
    # Baltic Sea
    baltic_sea = WaterTerritory('Baltic Sea', 'BAL', owner=None)
    # Skagerrak
    skagerrak = WaterTerritory('Skagerrak', 'SKA', owner=None)
    # Helgoland Bight
    helgoland_bight = WaterTerritory('Helgoland Bight', 'HEL', owner=None)
    # Irish Sea
    irish_sea = WaterTerritory('Irish Sea', 'IRI', owner=None)
    # English Channel
    english_channel = WaterTerritory('English Channel', 'ENG', owner=None)
    # Mid-Atlantic Ocean
    mid_atlantic_ocean = WaterTerritory('Mid-Atlantic Ocean', 'MAO', owner=None)
    # Gulf of Lyon
    gulf_of_lyon = WaterTerritory('Gulf of Lyon', 'GOL', owner=None)
    # Western Mediterranean
    western_mediterranean = WaterTerritory('Western Mediterranean', 'WME', owner=None)
    # Tyrrhenian Sea
    tyrrhenian_sea = WaterTerritory('Tyrrhenian Sea', 'TYS', owner=None)
    # Adriatic Sea
    adriatic_sea = WaterTerritory('Adriatic Sea', 'ADR', owner=None)
    # Ionian Sea
    ionian_sea = WaterTerritory('Ionian Sea', 'ION', owner=None)
    # Aegean Sea
    aegean_sea = WaterTerritory('Aegean Sea', 'AEG', owner=None)
    # Eastern Mediterranean
    eastern_mediterranean = WaterTerritory('Eastern Mediterranean', 'EMS', owner=None)
    # Black Sea
    black_sea = WaterTerritory('Black Sea', 'BLA', owner=None)

    # Adjacent Territories
    # --- Russia ---
    # Finland
    finland.set_adjacent(st_petersburg)
    finland.set_adjacent(norway)
    finland.set_adjacent(sweden)
    finland.set_adjacent(gulf_of_bothnia)
    # St. Petersburg (North/South Coast)
    st_petersburg.set_adjacent(moscow)
    st_petersburg.set_adjacent(livonia)
    st_petersburg.set_adjacent(norway)
    st_petersburg.set_adjacent(norway, coast=0) # North
    st_petersburg.set_adjacent(barents_sea, coast=0) # North
    st_petersburg.set_adjacent(finland, coast=1) # South
    st_petersburg.set_adjacent(livonia, coast=1) # South
    st_petersburg.set_adjacent(gulf_of_bothnia, coast=1) # South
    # Livonia
    livonia.set_adjacent(moscow)
    livonia.set_adjacent(warsaw)
    livonia.set_adjacent(prussia)
    livonia.set_adjacent(gulf_of_bothnia)
    livonia.set_adjacent(baltic_sea)
    # Moscow
    moscow.set_adjacent(warsaw)
    moscow.set_adjacent(ukraine)
    moscow.set_adjacent(sevastopol)
    # Warsaw
    warsaw.set_adjacent(ukraine)
    warsaw.set_adjacent(prussia)
    warsaw.set_adjacent(silesia)
    warsaw.set_adjacent(galicia)
    # Ukraine
    ukraine.set_adjacent(sevastopol)
    ukraine.set_adjacent(galicia)
    ukraine.set_adjacent(rumania)
    # Sevastopol
    sevastopol.set_adjacent(armenia)
    sevastopol.set_adjacent(rumania)
    sevastopol.set_adjacent(black_sea)

    # --- England ---
    # Edinburgh *
    edinburgh.set_adjacent(yorkshire)
    edinburgh.set_adjacent(liverpool)
    edinburgh.set_adjacent(clyde)
    edinburgh.set_adjacent(norwegian_sea)
    edinburgh.set_adjacent(north_sea)
    # Yorkshire
    yorkshire.set_adjacent(london)
    yorkshire.set_adjacent(wales)
    yorkshire.set_adjacent(liverpool)
    yorkshire.set_adjacent(north_sea)
    # London *
    london.set_adjacent(wales)
    london.set_adjacent(north_sea)
    london.set_adjacent(english_channel)
    # Wales
    wales.set_adjacent(liverpool)
    wales.set_adjacent(irish_sea)
    wales.set_adjacent(english_channel)
    # Liverpool *
    liverpool.set_adjacent(clyde)
    liverpool.set_adjacent(north_atlantic_ocean)
    liverpool.set_adjacent(irish_sea)
    # Clyde
    clyde.set_adjacent(north_atlantic_ocean)
    clyde.set_adjacent(norwegian_sea)

    # --- France ---
    # Brest *
    brest.set_adjacent(picardy)
    brest.set_adjacent(paris)
    brest.set_adjacent(gascony)
    brest.set_adjacent(english_channel)
    brest.set_adjacent(mid_atlantic_ocean)
    # Picardy
    picardy.set_adjacent(paris)
    picardy.set_adjacent(burgundy)
    picardy.set_adjacent(belgium)
    picardy.set_adjacent(english_channel)
    # Paris *
    paris.set_adjacent(burgundy)
    paris.set_adjacent(gascony)
    # Burgundy
    burgundy.set_adjacent(gascony)
    burgundy.set_adjacent(marseilles)
    burgundy.set_adjacent(ruhr)
    burgundy.set_adjacent(munich)
    burgundy.set_adjacent(belgium)
    # Gascony
    gascony.set_adjacent(marseilles)
    gascony.set_adjacent(spain)
    gascony.set_adjacent(mid_atlantic_ocean)
    # Marseilles *
    marseilles.set_adjacent(piedmont)
    marseilles.set_adjacent(spain)
    marseilles.set_adjacent(gulf_of_lyon)

    # --- Italy ---
    # Piedmont
    piedmont.set_adjacent(venice)
    piedmont.set_adjacent(tuscany)
    piedmont.set_adjacent(tyrolia)
    piedmont.set_adjacent(gulf_of_lyon)
    # Venice *
    venice.set_adjacent(tuscany)
    venice.set_adjacent(rome)
    venice.set_adjacent(apulia)
    venice.set_adjacent(tyrolia)
    venice.set_adjacent(trieste)
    venice.set_adjacent(adriatic_sea)
    # Tuscany
    tuscany.set_adjacent(rome)
    tuscany.set_adjacent(gulf_of_lyon)
    tuscany.set_adjacent(tyrrhenian_sea)
    # Rome *
    rome.set_adjacent(naples)
    rome.set_adjacent(apulia)
    rome.set_adjacent(tyrrhenian_sea)
    # Naples *
    naples.set_adjacent(apulia)
    naples.set_adjacent(tyrrhenian_sea)
    naples.set_adjacent(ionian_sea)
    # Apulia
    apulia.set_adjacent(adriatic_sea)
    apulia.set_adjacent(ionian_sea)

    # --- Germany ---
    # Kiel *
    kiel.set_adjacent(berlin)
    kiel.set_adjacent(ruhr)
    kiel.set_adjacent(munich)
    kiel.set_adjacent(denmark)
    kiel.set_adjacent(holland)
    kiel.set_adjacent(helgoland_bight)
    kiel.set_adjacent(baltic_sea)
    # Berlin *
    berlin.set_adjacent(prussia)
    berlin.set_adjacent(munich)
    berlin.set_adjacent(silesia)
    berlin.set_adjacent(baltic_sea)
    # Prussia
    prussia.set_adjacent(silesia)
    prussia.set_adjacent(baltic_sea)
    # Ruhr
    ruhr.set_adjacent(munich)
    ruhr.set_adjacent(belgium)
    ruhr.set_adjacent(holland)
    # Munich *
    munich.set_adjacent(silesia)
    munich.set_adjacent(bohemia)
    munich.set_adjacent(tyrolia)
    # Silesia
    silesia.set_adjacent(bohemia)
    silesia.set_adjacent(galicia)

    # --- Austria-Hungary ---
    # Bohemia
    bohemia.set_adjacent(galicia)
    bohemia.set_adjacent(vienna)
    bohemia.set_adjacent(tyrolia)
    # Galicia
    galicia.set_adjacent(vienna)
    galicia.set_adjacent(budapest)
    galicia.set_adjacent(rumania)
    # Vienna *
    vienna.set_adjacent(budapest)
    vienna.set_adjacent(tyrolia)
    vienna.set_adjacent(trieste)
    # Budapest *
    budapest.set_adjacent(trieste)
    budapest.set_adjacent(rumania)
    budapest.set_adjacent(serbia)
    # Tyrolia
    tyrolia.set_adjacent(trieste)
    # Trieste *
    trieste.set_adjacent(serbia)
    trieste.set_adjacent(albania)
    trieste.set_adjacent(adriatic_sea)

    # --- Turkey ---
    # Constantinople *
    constantinople.set_adjacent(ankara)
    constantinople.set_adjacent(smyrna)
    constantinople.set_adjacent(bulgaria)
    constantinople.set_adjacent(aegean_sea)
    constantinople.set_adjacent(black_sea)
    # Ankara *
    ankara.set_adjacent(armenia)
    ankara.set_adjacent(smyrna)
    ankara.set_adjacent(black_sea)
    # Armenia
    armenia.set_adjacent(smyrna)
    armenia.set_adjacent(syria)
    armenia.set_adjacent(black_sea)
    # Smyrna *
    smyrna.set_adjacent(syria)
    smyrna.set_adjacent(aegean_sea)
    smyrna.set_adjacent(eastern_mediterranean)
    # Syria
    syria.set_adjacent(eastern_mediterranean)

    # --- Uncontrolled ---
    # Norway *
    norway.set_adjacent(sweden)
    norway.set_adjacent(norwegian_sea)
    norway.set_adjacent(north_sea)
    norway.set_adjacent(skagerrak)
    # Sweden *
    sweden.set_adjacent(denmark)
    sweden.set_adjacent(gulf_of_bothnia)
    sweden.set_adjacent(baltic_sea)
    sweden.set_adjacent(skagerrak)
    # Denmark *
    denmark.set_adjacent(north_sea)
    denmark.set_adjacent(helgoland_bight)
    denmark.set_adjacent(skagerrak)
    denmark.set_adjacent(baltic_sea)
    # Holland *
    holland.set_adjacent(belgium)
    holland.set_adjacent(north_sea)
    holland.set_adjacent(helgoland_bight)
    # Belgium *
    belgium.set_adjacent(english_channel)
    belgium.set_adjacent(north_sea)
    # Portugal *
    portugal.set_adjacent(spain)
    portugal.set_adjacent(mid_atlantic_ocean)
    # Spain * (North/South Coast)
    spain.set_adjacent(gascony, coast=0) # North
    spain.set_adjacent(portugal, coast=0) # North
    spain.set_adjacent(mid_atlantic_ocean, coast=0) # North
    spain.set_adjacent(portugal, coast=1) # South
    spain.set_adjacent(mid_atlantic_ocean, coast=1) # South
    spain.set_adjacent(western_mediterranean, coast=1) # South
    spain.set_adjacent(gulf_of_lyon, coast=1) # South
    # North Africa
    north_africa.set_adjacent(tunis)
    north_africa.set_adjacent(mid_atlantic_ocean)
    north_africa.set_adjacent(western_mediterranean)
    # Tunis *
    tunis.set_adjacent(western_mediterranean)
    tunis.set_adjacent(tyrrhenian_sea)
    tunis.set_adjacent(ionian_sea)
    # Rumania *
    rumania.set_adjacent(bulgaria)
    rumania.set_adjacent(serbia)
    rumania.set_adjacent(black_sea)
    # Bulgaria * (North/South Coast)
    bulgaria.set_adjacent(serbia)
    bulgaria.set_adjacent(greece)
    bulgaria.set_adjacent(constantinople, coast=0) # North
    bulgaria.set_adjacent(rumania, coast=0) # North
    bulgaria.set_adjacent(black_sea, coast=0) # North
    bulgaria.set_adjacent(constantinople, coast=1) # South
    bulgaria.set_adjacent(greece, coast=1) # South
    bulgaria.set_adjacent(aegean_sea, coast=1) # South
    # Serbia *
    serbia.set_adjacent(albania)
    serbia.set_adjacent(greece)
    # Albania
    albania.set_adjacent(greece)
    albania.set_adjacent(adriatic_sea)
    albania.set_adjacent(ionian_sea)
    # Greece *
    greece.set_adjacent(ionian_sea)
    greece.set_adjacent(aegean_sea)

    # --- Water ---
    # North Atlantic Ocean
    north_atlantic_ocean.set_adjacent(norwegian_sea)
    north_atlantic_ocean.set_adjacent(irish_sea)
    north_atlantic_ocean.set_adjacent(mid_atlantic_ocean)
    # Norwegian Sea
    norwegian_sea.set_adjacent(barents_sea)
    norwegian_sea.set_adjacent(north_sea)
    # Barents Sea
    # North Sea
    north_sea.set_adjacent(skagerrak)
    north_sea.set_adjacent(helgoland_bight)
    north_sea.set_adjacent(english_channel)
    # Gulf of Bothnia
    gulf_of_bothnia.set_adjacent(baltic_sea)
    # Baltic Sea
    # Skagerrak
    # Helgoland Bight
    # Irish Sea
    irish_sea.set_adjacent(english_channel)
    irish_sea.set_adjacent(mid_atlantic_ocean)
    # English Channel
    english_channel.set_adjacent(mid_atlantic_ocean)
    # Mid-Atlantic Ocean
    mid_atlantic_ocean.set_adjacent(western_mediterranean)
    # Gulf of Lyon
    gulf_of_lyon.set_adjacent(western_mediterranean)
    gulf_of_lyon.set_adjacent(tyrrhenian_sea)
    # Western Mediterranean
    western_mediterranean.set_adjacent(tyrrhenian_sea)
    # Tyrrhenian Sea
    tyrrhenian_sea.set_adjacent(ionian_sea)
    # Adriatic Sea
    adriatic_sea.set_adjacent(ionian_sea)
    # Ionian Sea
    ionian_sea.set_adjacent(aegean_sea)
    ionian_sea.set_adjacent(eastern_mediterranean)
    # Aegean Sea
    aegean_sea.set_adjacent(eastern_mediterranean)
    # Eastern Mediterranean
    # Black Sea

    territories = [
        finland,
        st_petersburg,
        livonia,
        moscow,
        warsaw,
        ukraine,
        sevastopol,
        edinburgh,
        yorkshire,
        london,
        wales,
        liverpool,
        clyde,
        brest,
        picardy,
        paris,
        burgundy,
        gascony,
        marseilles,
        piedmont,
        venice,
        tuscany,
        rome,
        naples,
        apulia,
        kiel,
        berlin,
        prussia,
        ruhr,
        munich,
        silesia,
        bohemia,
        galicia,
        vienna,
        budapest,
        tyrolia,
        trieste,
        constantinople,
        ankara,
        armenia,
        smyrna,
        syria,
        norway,
        sweden,
        denmark,
        holland,
        belgium,
        portugal,
        spain,
        north_africa,
        tunis,
        rumania,
        bulgaria,
        serbia,
        albania,
        greece,
        north_atlantic_ocean,
        norwegian_sea,
        barents_sea,
        north_sea,
        gulf_of_bothnia,
        baltic_sea,
        skagerrak,
        helgoland_bight,
        irish_sea,
        english_channel,
        mid_atlantic_ocean,
        gulf_of_lyon,
        western_mediterranean,
        tyrrhenian_sea,
        adriatic_sea,
        ionian_sea,
        aegean_sea,
        eastern_mediterranean,
        black_sea,
    ]
    map_object.territories = territories
    map_object.russia = russia
    map_object.england = england
    map_object.france = france
    map_object.italy = italy
    map_object.germany = germany
    map_object.austria_hungary = austria_hungary
    map_object.turkey = turkey

    map_object.players = [russia, england, france, italy, germany, austria_hungary, turkey]

    map_object.finland = finland
    map_object.st_petersburg = st_petersburg
    map_object.livonia = livonia
    map_object.moscow = moscow
    map_object.warsaw = warsaw
    map_object.ukraine = ukraine
    map_object.sevastopol = sevastopol
    map_object.edinburgh = edinburgh
    map_object.yorkshire = yorkshire
    map_object.london = london
    map_object.wales = wales
    map_object.liverpool = liverpool
    map_object.clyde = clyde
    map_object.brest = brest
    map_object.picardy = picardy
    map_object.paris = paris
    map_object.burgundy = burgundy
    map_object.gascony = gascony
    map_object.marseilles = marseilles
    map_object.piedmont = piedmont
    map_object.venice = venice
    map_object.tuscany = tuscany
    map_object.rome = rome
    map_object.naples = naples
    map_object.apulia = apulia
    map_object.kiel = kiel
    map_object.berlin = berlin
    map_object.prussia = prussia
    map_object.ruhr = ruhr
    map_object.munich = munich
    map_object.silesia = silesia
    map_object.bohemia = bohemia
    map_object.galicia = galicia
    map_object.vienna = vienna
    map_object.budapest = budapest
    map_object.tyrolia = tyrolia
    map_object.trieste = trieste
    map_object.constantinople = constantinople
    map_object.ankara = ankara
    map_object.armenia = armenia
    map_object.smyrna = smyrna
    map_object.syria = syria
    map_object.norway = norway
    map_object.sweden = sweden
    map_object.denmark = denmark
    map_object.holland = holland
    map_object.belgium = belgium
    map_object.portugal = portugal
    map_object.spain = spain
    map_object.north_africa = north_africa
    map_object.tunis = tunis
    map_object.rumania = rumania
    map_object.bulgaria = bulgaria
    map_object.serbia = serbia
    map_object.albania = albania
    map_object.greece = greece
    map_object.north_atlantic_ocean = north_atlantic_ocean
    map_object.norwegian_sea = norwegian_sea
    map_object.barents_sea = barents_sea
    map_object.north_sea = north_sea
    map_object.gulf_of_bothnia = gulf_of_bothnia
    map_object.baltic_sea = baltic_sea
    map_object.skagerrak = skagerrak
    map_object.helgoland_bight = helgoland_bight
    map_object.irish_sea = irish_sea
    map_object.english_channel = english_channel
    map_object.mid_atlantic_ocean = mid_atlantic_ocean
    map_object.gulf_of_lyon = gulf_of_lyon
    map_object.western_mediterranean = western_mediterranean
    map_object.tyrrhenian_sea = tyrrhenian_sea
    map_object.adriatic_sea = adriatic_sea
    map_object.ionian_sea = ionian_sea
    map_object.aegean_sea = aegean_sea
    map_object.eastern_mediterranean = eastern_mediterranean
    map_object.black_sea = black_sea