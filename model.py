
from config import app, db
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100))
    created = db.Column(db.DateTime)
    location = db.Column(db.String(100))
    phone = db.Column(db.Integer)
    email = db.Column(db.String(100))


class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    name = db.Column(db.String(100))
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))
    phone = db.Column(db.Integer)
    email = db.Column(db.String(100))
    created = db.Column(db.DateTime)

    org_ids = relationship('Organization', foreign_keys='User.org_id')


class ServiceType(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100))


class GeneralizedDialplan(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    dialplan = db.Column(JSON)
    previous_version_id = db.Column(db.Integer)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    service_type = db.Column(db.Integer, db.ForeignKey('service_type.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('generalized_dialplan.id'))
    extension = db.Column(db.Integer)
    isActive = db.Column(db.Boolean)
    created = db.Column(db.DateTime)
    allocated_channels = db.Column(db.Integer)
    channels_inuse = db.Column(db.Integer)

    org_ids = relationship('Organization', foreign_keys='Service.org_id')
    service_types = relationship('ServiceType', foreign_keys='Service.service_type')
    service_ids = relationship('GeneralizedDialplan', foreign_keys='Service.service_id')


class GeneralizedDataIncoming(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    generalized_dialplan_id = db.Column(db.Integer, db.ForeignKey('generalized_dialplan.id'))
    data = db.Column(JSON)
    incoming_number = db.Column(db.Integer)

    dialplan_ids = relationship('GeneralizedDialplan', foreign_keys='GeneralizedDataIncoming.generalized_dialplan_id')


class GeneralizedDataOutgoing(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    generalized_dialplan_id = db.Column(db.Integer, db.ForeignKey('generalized_dialplan.id'))
    data = db.Column(JSON)
    outgoing_number = db.Column(db.Integer)

    dialplan_ids = relationship('GeneralizedDialplan', foreign_keys='GeneralizedDataOutgoing.generalized_dialplan_id')


class IncomingLog(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    service = db.Column(db.String(100))
    call_start_time = db.Column(db.DateTime)
    call_end_time = db.Column(db.DateTime)
    call_duration = db.Column(db.Float)
    complete = db.Column(db.Boolean)
    incoming_number = db.Column(db.Integer)
    extension = db.Column(db.Integer)
    status = db.Column(db.String(100))
    generalized_data_incoming = db.Column(db.Integer)

    org_ids = relationship('Organization', foreign_keys='IncomingLog.org_id')


class OutgoingLog(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    service = db.Column(db.String(100))
    call_start_time = db.Column(db.DateTime)
    call_end_time = db.Column(db.DateTime)
    call_duration = db.Column(db.Float)
    complete = db.Column(db.Boolean)
    phone = db.Column(db.Integer)
    status = db.Column(db.String(100))

    org_ids = relationship('Organization', foreign_keys='OutgoingLog.org_id')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    log_id = db.Column(db.Integer, db.ForeignKey('incoming_log.id'))
    comment = db.Column(db.String(500))


if __name__ == '__main__':
    manager.run()
