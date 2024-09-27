# ALL Commads/Features

() - obvezen 
[] neobvezen

# Kategorije
* [Komande za tedensko tekmovanje](#komande-za-tedensko-tekmovanje)
* [WCA komande](#wca-komande)
* [Komande za moderatorje](#komande-za-moderatorje)
-----
## Komande za tedensko tekmovanje 
* [Solves](#solves)
* [Weeksolves](#weeksolves)

-----
### Solves
> Vnos časov za TT / Enter times for WC

Uporaba:
/solves

| ![solves](/assets/images/guide/solves.png) | 
|:--:| 
| *Izberi glavne ali stranske discipline* |

| ![solves2](/assets/images/guide/solves2.png) | 
|:--:| 
| *Vnesi čase* |

Format: 1.23, 12.34, 1:23.45, 12:34.56, DNF
* `,` med časi
* `MM:SS.ms`
* `-1`ali `DNF` za DNF
* +2 mora biti prištet končnemu času

### Weeksolves
Poglej čase od drugih za ta teden / See times of other for this week

Uporaba: /weeksolves (@Mankifg)
* @Mankifg: oseba, privzeto: ti

Prikaz časev je enak kot pri [Solvih](#solves),


## WCA komande
Komande za podatke iz WCA spletne strani

* [Spremeni wca id](#changewcaid)
* [Tekmovanje](#comp)
* [WCA Profil](#wcap)

### changewcaid
Spremeni wca id povezan z discord računom / change wca id connected with discord account

Uporaba: /changewcaid (wca id)

NOTE: Trenutno ni nobenega sistema, ki preveri če je uporabnik res lastnik wca računa 

### comp
Info glede wca tekmovanja / Info about wca competition

Uporaba: /comp (id)
* id: id wca tekmovanja

| ![solves](/assets/images/guide/comp.png) | 
|:--:| 
| *Primer za SlovenianNationals2024* |

### wcap
Informacije glede wca profila / Info about wca profile

Uporaba: /wcap [id] [@]
* id: wca id, privzeto: tvoj [če si ga povezal](#changewcaid)
* @: omemba uporabnika, uporabi njegov id če ga je povezal

Bot sprejeme wca id ali omemba s prednostjo na idju

| ![solves](/assets/images/guide/wcap_max_park.png) | 
|:--:| 
| *Primer za Max Parka ([2012PARK03](https://www.worldcubeassociation.org/persons/2012PARK03))* |

### Iskalec prijavljenih tekmovalcev
Poišče prijavljene tekmovalce glede na regijo / Finds registered competitors by region

Uporaba: /userfinder (regija) [začetek] [konec]
* regija: npr. Slovenia
* začetek: zaćetni datum format YYYY-MM-DD, privzeto: dananšnji dan
* konec: kočni datum format YYYY-MM-DD, privzeto: začetek + 7d
* BONUS: konec je lahko tudi število dni of začetka

| ![solves](/assets/images/guide/userfinder.png) | 
|:--:| 
| *Primer za iskanje* |

-----
## Komande za moderatorje: 
!: Vse komande potrebujejo mod rolo

* [Scrambles](#scrambles)
* [Modforce](#modforce)
* [Newweek](#newweek)

-----
### Scrambles
> Generiranje tedenskih mešalnih algoritmov / Generates weeky scrambles

Uporaba: /scrambles

### Modforce
> Izbriši tedenske časa izbranega uporabnika / Deleted the weeky times for user

Uporaba: /modforce (@oseba)

### Newweek
> Manualno preklopi teden / Maunaly change week

Uporaba: /modforce (ime tedna)
