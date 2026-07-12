# Component Diagram Knowledge Base

This document contains canonical PlantUML component diagram examples to demonstrate correct syntax, structure, and best practices.

## 1. Basic Component and Actor

**GOOD:**
```plantuml
@startuml
actor "System User" as User
component "Core System" as Core

User --> Core : Uses
@enduml
```

**BAD:**
```plantuml
@startuml
User -> Core System : Uses
@enduml
```
**Reason why BAD is incorrect:** Actors and components must be explicitly declared before use, especially when they contain spaces. Arrow syntax `->` is typical for sequence diagrams; component diagrams generally use `-->`.

## 2. Databases and Stereotypes

**GOOD:**
```plantuml
@startuml
component "Data Processing" as Processor <<Service>>
database "Primary Storage" as DB <<PostgreSQL>>

Processor --> DB : Reads/Writes
@enduml
```

**BAD:**
```plantuml
@startuml
component Processor <<Service>>
database Primary Storage <<PostgreSQL>>
Processor --> Primary Storage : Reads/Writes
@enduml
```
**Reason why BAD is incorrect:** Strings with spaces like "Primary Storage" must be enclosed in quotes when defining the element. 

## 3. Packages for Grouping

**GOOD:**
```plantuml
@startuml
package "Frontend Layer" {
    component "Web Interface" as Web
    component "Mobile Interface" as Mobile
}

package "Backend Layer" {
    component "API Controller" as API
}

Web --> API : REST
Mobile --> API : REST
@enduml
```

**BAD:**
```plantuml
@startuml
group Frontend Layer {
    component Web
}
@enduml
```
**Reason why BAD is incorrect:** `group` is a keyword used in sequence diagrams. In component diagrams, `package`, `node`, `folder`, or `cloud` must be used for grouping elements.

## 4. Interfaces and Provided/Required Ports

**GOOD:**
```plantuml
@startuml
component "Module A" as ModA
interface "Data Sync API" as SyncAPI
component "Module B" as ModB

ModA -up-> SyncAPI : Requires
SyncAPI -down- ModB : Provides
@enduml
```

**BAD:**
```plantuml
@startuml
component ModA
interface SyncAPI
component ModB

ModA => SyncAPI
SyncAPI <= ModB
@enduml
```
**Reason why BAD is incorrect:** `=>` and `<=` are not valid directional arrows for linking components and interfaces in PlantUML component diagrams. Use standard dashed lines (`..>`), solid lines (`-->`), or directional lines (`-up->`, `-down->`).

## 5. Cloud and External Systems

**GOOD:**
```plantuml
@startuml
component "Internal Processing" as Internal
cloud "Third-Party Provider" <<External>> {
    component "External API" as ExtAPI
}

Internal --> ExtAPI : HTTPS
@enduml
```

**BAD:**
```plantuml
@startuml
component Internal
External API <<External>>
Internal -> External API : HTTPS
@enduml
```
**Reason why BAD is incorrect:** "External API" is used without a declaration, contains a space without quotes, and `cloud` grouping is missing. Stereotypes (`<<External>>`) must be placed at the declaration.

## 6. Labeled Arrows and Direction

**GOOD:**
```plantuml
@startuml
component "Service A" as A
component "Service B" as B
component "Service C" as C

A -right-> B : Sends Data
B -down-> C : Forwards Request
C -left-> A : Callback
@enduml
```

**BAD:**
```plantuml
@startuml
component A
component B
A ---> B : Sends Data
B <---- C : Forwards Request
@enduml
```
**Reason why BAD is incorrect:** Using multiple hyphens (`--->` or `<----`) is discouraged and can lead to unpredictable layouts or syntax errors. Use directional hints (`-right->`, `-down->`) if layout control is needed.

## 7. Nested Components

**GOOD:**
```plantuml
@startuml
component "Main System" as Main {
    component "Subsystem 1" as Sub1
    component "Subsystem 2" as Sub2
    
    Sub1 --> Sub2 : Internal Call
}

actor User
User --> Sub1 : Initiates
@enduml
```

**BAD:**
```plantuml
@startuml
component "Main System" as Main
component Main.Sub1
component Main.Sub2
@enduml
```
**Reason why BAD is incorrect:** Dot notation (`Main.Sub1`) is not valid for nesting components. You must declare the outer component using braces `{}` and place the inner components inside.

## 8. Explicit Ports

**GOOD:**
```plantuml
@startuml
component "Processing Engine" as Engine {
    port "Inbound" as In
    port "Outbound" as Out
}

component "Source" as Src
component "Destination" as Dest

Src --> In
Out --> Dest
@enduml
```

**BAD:**
```plantuml
@startuml
component Engine
port Inbound
port Outbound
Engine -> Inbound
Engine -> Outbound
@enduml
```
**Reason why BAD is incorrect:** Ports must be declared inside the component definition block using `{}`. Floating ports disconnected from a component body violate PlantUML semantics.
