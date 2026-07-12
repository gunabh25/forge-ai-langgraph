from agents.uml_generator.sequence_validator import SequenceValidator

plan = '{"actors": ["User"], "major_components": [{"name": "Auth Service"}]}'
puml = '''@startuml
actor User
participant "Auth Backend" as auth
User -> auth: login
@enduml
'''
validator = SequenceValidator()
res = validator.validate(plan, puml)
print("Score:", res.score)
print("Traceable:", res.traceable_participants)
print("Non Traceable:", res.non_traceable_participants)
