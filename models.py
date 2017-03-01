from peewee import *
from playhouse.postgres_ext import *

database = PostgresqlDatabase('voiceinndb', **{'user': 'ano'})

class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database

class Organization(BaseModel):
    created = DateTimeField(null=True)
    email = CharField(null=True)
    location = CharField(null=True)
    name = CharField(null=True)
    phone = BigIntegerField(null=True)

    class Meta:
        db_table = 'organization'

class ServiceType(BaseModel):
    name = CharField(null=True)

    class Meta:
        db_table = 'service_type'

class GeneralizedDialplan(BaseModel):
    dialplan = JSONField(null=True)
    previous_version = IntegerField(db_column='previous_version_id', null=True)
    service_type = ForeignKeyField(db_column='service_type', null=True, rel_model=ServiceType, to_field='id')

    class Meta:
        db_table = 'generalized_dialplan'

class GeneralizedDataIncoming(BaseModel):
    data = JSONField(null=True)
    generalized_dialplan = ForeignKeyField(db_column='generalized_dialplan_id', null=True, rel_model=GeneralizedDialplan, to_field='id')
    incoming_number = CharField(null=True)

    class Meta:
        db_table = 'generalized_data_incoming'

class IncomingLog(BaseModel):
    call_duration = FloatField(null=True)
    call_end_time = DateTimeField(null=True)
    call_start_time = DateTimeField(null=True)
    completecall = BooleanField(db_column='completeCall', null=True)
    extension = CharField(null=True)
    generalized_data_incoming = ForeignKeyField(db_column='generalized_data_incoming_id', null=True, rel_model=GeneralizedDataIncoming, to_field='id')
    incoming_number = CharField(null=True)
    org = ForeignKeyField(db_column='org_id', null=True, rel_model=Organization, to_field='id')
    service = CharField(null=True)

    class Meta:
        db_table = 'incoming_log'

class Comment(BaseModel):
    comment = CharField(null=True)
    log = ForeignKeyField(db_column='log_id', null=True, rel_model=IncomingLog, to_field='id')
    status = CharField(null=True)

    class Meta:
        db_table = 'comment'

class GeneralizedDataOutgoing(BaseModel):
    data = JSONField(null=True)
    generalized_dialplan = ForeignKeyField(db_column='generalized_dialplan_id', null=True, rel_model=GeneralizedDialplan, to_field='id')
    outgoing_number = BigIntegerField(null=True)

    class Meta:
        db_table = 'generalized_data_outgoing'

class OutgoingLog(BaseModel):
    call_duration = FloatField(null=True)
    call_time = DateTimeField(null=True)
    complete = BooleanField(null=True)
    org = ForeignKeyField(db_column='org_id', null=True, rel_model=Organization, to_field='id')
    phone = BigIntegerField(null=True)
    service = CharField(null=True)

    class Meta:
        db_table = 'outgoing_log'

class Services(BaseModel):
    allocated_channels = IntegerField(null=True)
    channels_inuse = IntegerField(null=True)
    created = DateTimeField(null=True)
    extension = CharField(null=True)
    isactive = BooleanField(null=True)
    org = ForeignKeyField(db_column='org_id', null=True, rel_model=Organization, to_field='id')
    service = ForeignKeyField(db_column='service_id', null=True, rel_model=GeneralizedDialplan, to_field='id')
    service_type = ForeignKeyField(db_column='service_type', null=True, rel_model=ServiceType, to_field='id')

    class Meta:
        db_table = 'services'

class Users(BaseModel):
    created = DateTimeField(null=True)
    email = CharField(null=True)
    name = CharField(null=True)
    org = ForeignKeyField(db_column='org_id', null=True, rel_model=Organization, to_field='id')
    password = CharField(null=True)
    phone = BigIntegerField(null=True)
    username = CharField(null=True)

    class Meta:
        db_table = 'users'

