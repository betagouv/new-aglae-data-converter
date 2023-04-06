## Overview

```mermaid
flowchart TD
    A[Acquisition par New Aglae] --> |génère| L(LST) & G(Global)
    L & G --> M{Moulinette}
    C[/lst config/]
    C -.-> M
    Gs(globals.hdf5) -.-> |inject| M
    M --> |créer| LH(LST.hdf5)
    M --> |ajoute| Gs_out(globals.hdf5)
```

## Scénario: LST Seul

Exemple d'un LST avec 4 detecteur HE1, HE2, HE3, HE4, ainsi qu'un detecteur sommet HE10 ayant pour source les 4 detecteurs physique.

```mermaid
flowchart TD
    L[projet.lst] --> moulinette
    C[lst_config.yml] --> moulinette
    subgraph moulinette
        E{Extrait} --> |cmd header| Exp(Experience Info) & Map(Map Info)
        E --> D(Raw Data)
        Exp -.-> GroupAttributes
        D -.-> HE1 & HE2 & HE3 & HE4
        Merge{Merge pour HE10}
        D --> Merge
        Merge -.-> HE10
        subgraph projet.hdf5
            subgraph group data
                GroupAttributes[/attributs du\ngroupe data/]
                HE1
                HE2
                HE3
                HE4
                HE10[HE10\nattributes: sources HE1, HE2, HE3, HE4]
            end
        end
    end
```

Config pour ce formatage:

```yml
# lst_config.yml
x: 256
y: 512
detectors:
  HE1:
    adc: 1
    channels: 2048
  HE2:
    adc: 2
    channels: 2048
  HE3:
    adc: 4
    channels: 2048
  HE4:
    adc: 8
    channels: 2048
  HE10: ["HE1", "HE2", "HE3", "HE4"]
```

### HDF5

LE hdf5 resultant aura la forme suivante:

```
projet.lst
    -- data # group
        attributes:
            beam_energy: 3000keV
            he1_filter: 100umAl
            he2_filter: OFF
            he3_filter: 100umAl
            he4_filter: 100umAl
            le0_filter: 40mmHe
            particle: Proton
        -- HE1 # dataset
        -- HE2
        -- HE3
        -- HE4
        -- HE10
            attributes:
                source: HE1, HE2, HE3, HE4
```

## Scenario: Globals

```mermaid
flowchart TD
    D[dossiers de\n.x1, .r9 etc]
    G[globals.hdf5]
    M{moulinette}
    D --> M
    G -.-> |existant optionnel| M
    M --> |Ajoute ou créer| globals
    subgraph globals
        direction LR
        subgraph 0001
            attr_0001[attributes:\nref object\nstart date]
        end
        0002
        0003
        ...
    end
```
