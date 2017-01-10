"""
/***************************************************************************
Name                 : Widget factories
Description          : Creates appropriate form widgets for an entity.
Date                 : 8/June/2016
copyright            : (C) 2016 by UN-Habitat and implementing partners.
                       See the accompanying file CONTRIBUTORS.txt in the root
email                : stdm@unhabitat.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from collections import OrderedDict
from datetime import (
    date,
    datetime
)

from PyQt4.QtCore import QCoreApplication
from PyQt4.QtGui import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QMouseEvent,
    QPixmap,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QToolTip,
    QWidget
)

from stdm.data.configuration.columns import (
    AdministrativeSpatialUnitColumn,
    BaseColumn,
    BooleanColumn,
    DateColumn,
    DateTimeColumn,
    DoubleColumn,
    ForeignKeyColumn,
    IntegerColumn,
    LookupColumn,
    MultipleSelectColumn,
    PercentColumn,
    TextColumn,
    VarCharColumn
)
from stdm.data.configuration import entity_model
from stdm.settings import current_profile
from stdm.ui.customcontrols.relation_line_edit import (
    AdministrativeUnitLineEdit,
    RelatedEntityLineEdit
)
from stdm.ui.customcontrols.multi_select_view import MultipleSelectTreeView

class WidgetException(Exception):
    """General exceptions thrown when creating form widgets."""
    pass

class UserTipLabel(QLabel):
    """
    Custom label that shows an information icon and a tip containing the
    column user tip value as specified in the configuration.
    """
    def __init__(self, parent=None, user_tip=None):
        QLabel.__init__(self, parent)

        #Set size policy
        self.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Fixed,
                QSizePolicy.Fixed
            )
        )

        self.setMouseTracking(True)

        #Set tip icon
        self._set_tip_icon()

        #Customize appearance of the tooltip
        self.setStyleSheet(
            'QToolTip { color: #ffffff; background-color: #2a82da; '
            'border: 1px solid white; }'
        )

        #Initialize user tip
        if user_tip is None:
            self._user_tip = ''
        else:
            self._user_tip = user_tip

    def _set_tip_icon(self):
        #Set the information icon
        self._px = QPixmap(':/plugins/stdm/images/icons/user_tip.png')
        self.setPixmap(self._px)

    def pixmap(self):
        """
        :return: Returns the pixmap object associated with this label.
        Overrides the default implementation.
        :rtype: QPixmap
        """
        return self._px

    def mouseMoveEvent(self, mouseEvent):
        """
        Override so that the tool tip can be shown immediately.
        :param mouseEvent: Mouse move event
        :type mouseEvent: QMouseEvent
        """
        QToolTip.showText(mouseEvent.globalPos(), self._user_tip, self)

    @property
    def user_tip(self):
        """
        :return: Returns the user tip corresponding to this label.
        :rtype: str
        """
        return self._user_tip

    @user_tip.setter
    def user_tip(self, value):
        """
        Sets the user tip for this label.
        :param value: User tip text.
        :type value: str
        """
        if not value:
            return

        self._user_tip = value


class EntityValueFormatter(object):
    """"
    Provides a convenient way of formatting the values of an entity's column
    to more friendly display values.
    """
    def __init__(self, **kwargs):
        self.entity_name = kwargs.get('name', '')
        self.entity = kwargs.get('entity', None)

        self._current_profile = current_profile()

        #Use entity name to set entity object
        if self.entity is None and self.entity_name:
            if not self._current_profile is None:
                self.entity = self._current_profile.entity_by_name(
                    self.entity_name
                )

        #User-defined column widgets collection
        self._registered_columns = {}

    @property
    def registered_columns(self):
        """
        :return: Returns the registered column widget collection containing
        the name of the column and corresponding widget handler.
        :rtype: dict
        """
        return self._registered_columns

    def register_column(self, name):
        """
        Adds the column with the given name to the list of registered columns.
        :param name: Name of the column.
        :type name: str
        :return: Returns True if the column was successfully registered,
        otherwise False if the column does not exist in the entity or
        if it is already registered.
        :rtype: bool
        """
        if self.entity is None:
            return False

        if name in self._registered_columns:
            return False

        column = self.entity.column(name)

        if column is None:
            return False

        value_handler_cls = ColumnWidgetRegistry.factory(column.TYPE_INFO)
        value_handler = value_handler_cls(column)

        #Add handler to collection
        self._registered_columns[name] = value_handler

        return True

    def register_columns(self, columns):
        """
        Registers multiple columns based on their name.
        :param columns: Column names
        :type columns: list
        :return: Returns True if all the columns were successfully
        registered, otherwise False.
        :rtype: bool
        """
        state = False

        for c in columns:
            state = self.register_column(c)

        return state

    def value_handler(self, name):
        """
        :param name: Name of the column.
        :type name: str
        :return: Returns the value handler for the registered column with the given name.
        :rtype: ColumnWidgetRegistry
        """
        return self._registered_columns.get(name, None)

    def column_display_value(self, name, value):
        """
        Formats the value of the given column name to a more friendly display
        value such as for lookups, administrative spatial unit etc.
        :param name: Name of the column.
        :type name: str
        :param value: Column value
        :type value: object
        :return: Returns the friendly display value or an empty string if the
        columns was not registered or there is no matching value.
        :rtype: str
        """
        if not name in self._registered_columns:
            return value

        value_handler = self._registered_columns.get(name)

        return value_handler.format_column_value(value)


class ColumnWidgetRegistry(object):
    """
    Base container for widget factories based on column types. It is used to
    create widgets based on column type.
    """
    registered_factories = OrderedDict()

    COLUMN_TYPE_INFO = 'NA'
    _TYPE_PREFIX = ''

    def __init__(self, column):
        """
        Class constructor.
        :param column: Column object corresponding to the widget factory.
        :type column: BaseColumn
        """
        self._column = column

    @property
    def column(self):
        """
        :return: Returns column object associated with this factory.
        :rtype: BaseColumn
        """
        return self._column

    @classmethod
    def register(cls):
        """
        Adds the widget factory to the collection based on column type info.
        :param cls: Column widget factory class.
        :type cla: ColumnWidgetRegistry
        """
        ColumnWidgetRegistry.registered_factories[cls.COLUMN_TYPE_INFO] = cls

    @classmethod
    def create(cls, c, parent=None):
        """
        Creates the appropriate widget based on the given column type.
        :param c: Column object for which to create a widget for.
        :type c: BaseColumn
        :param parent: Parent widget.
        :type parent: QWidget
        :return: Returns a widget for the given column type only if there is
        a corresponding factory in the registry, otherwise returns None.
        :rtype: QWidget
        """
        factory = ColumnWidgetRegistry.factory(c.TYPE_INFO)

        if not factory is None:
            w = factory._create_widget(c, parent)
            factory._widget_configuration(w, c)

            return w

        return None

    @classmethod
    def factory(cls, type_info):
        """
        :param type_info: Type info of a given column.
        :type type_info: str
        :return: Returns a widget factory based on the corresponding type
        info, otherwise None if there is no registered factory with the given
        type_info name.
        """
        return ColumnWidgetRegistry.registered_factories.get(
                type_info,
                None
        )

    @classmethod
    def _create_widget(cls, c, parent):
        #For implementation by sub-classes to create the appropriate widget.
        raise NotImplementedError

    @classmethod
    def _widget_configuration(cls, widget, c):
        """
        For optionally configurating the widget created by :func:`_create_widget`.
        To be implemnted by sub-classes as default implementation does nothing.
        .. versionadded:: 1.5
        """
        pass

    def format_column_value(self, value):
        """
        Formats the column value to a more friendly display value. Should be
        implemented by sub-classes for custom behavior. Default
        implementation converts the value to a unicode object.
        :return: Returns a more user-friendly display.
        :rtype: str
        """
        return unicode(value)


class VarCharWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for VarChar column type.
    """
    COLUMN_TYPE_INFO = VarCharColumn.TYPE_INFO
    _TYPE_PREFIX = 'le_'

    @classmethod
    def _create_widget(cls, c, parent):
        le = QLineEdit(parent)
        le.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))
        le.setMaxLength(c.maximum)

        return le

    def format_column_value(self, value):
        if value is None:
            return ''

        return super(VarCharWidgetFactory, self).format_column_value(value)

VarCharWidgetFactory.register()


class TextWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for Text column type.
    """
    COLUMN_TYPE_INFO = TextColumn.TYPE_INFO
    _TYPE_PREFIX = 'txt_'

    @classmethod
    def _create_widget(cls, c, parent):
        te = QTextEdit(parent)
        te.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        return te

TextWidgetFactory.register()


class DateWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for Date column type.
    """
    COLUMN_TYPE_INFO = DateColumn.TYPE_INFO
    _TYPE_PREFIX = 'dt_'

    @classmethod
    def _create_widget(cls, c, parent):
        dt = QDateEdit(parent)
        dt.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))
        dt.setCalendarPopup(True)

        #Set ranges
        if c.min_use_current_date:
            dt.setMinimumDate(date.today())
        else:
            dt.setMinimumDate(c.minimum)

        if c.max_use_current_date:
            dt.setMaximumDate(date.today())
        else:
            dt.setMaximumDate(c.maximum)

        #Set maximum date as current date
        dt.setDate(date.today())

        return dt

    def format_column_value(self, value):
        #Format date to string
        if not value is None:
            return value.strftime('%x')

        else:
            return ''

DateWidgetFactory.register()


class DateTimeWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for DateTime column type.
    """
    COLUMN_TYPE_INFO = DateTimeColumn.TYPE_INFO
    _TYPE_PREFIX = 'dtt_'

    @classmethod
    def _create_widget(cls, c, parent):
        dtt = QDateTimeEdit(parent)
        dtt.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))
        dtt.setCalendarPopup(True)

        #Set ranges
        if c.min_use_current_datetime:
            dtt.setMinimumDateTime(datetime.today())
        else:
            dtt.setMinimumDateTime(c.minimum)

        if c.max_use_current_datetime:
            dtt.setMaximumDateTime(datetime.today())
        else:
            dtt.setMaximumDateTime(c.maximum)

        #Set maximum datetime as current datetime
        dtt.setDateTime(dtt.maximumDateTime())

        return dtt

    def format_column_value(self, value):
        #Format datetime
        if not value is None:
            return value.strftime('%c')

        else:
            return ''

DateTimeWidgetFactory.register()


class IntegerWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for integer column type.
    """
    COLUMN_TYPE_INFO = IntegerColumn.TYPE_INFO
    _TYPE_PREFIX = 'sb_'

    @classmethod
    def _create_widget(cls, c, parent):
        sb = QSpinBox(parent)
        sb.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        #Set ranges
        c_min = sb.valueFromText(str(c.minimum))
        c_max = sb.valueFromText(str(c.maximum))
        sb.setMinimum(c.minimum)
        sb.setMaximum(c.maximum)

        return sb

    def format_column_value(self, value):
        #Format int to string
        if not value is None:
            return str(value)

IntegerWidgetFactory.register()


class DoubleWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for double column type.
    """
    COLUMN_TYPE_INFO = DoubleColumn.TYPE_INFO
    _TYPE_PREFIX = 'dsb_'

    @classmethod
    def _create_widget(cls, c, parent):
        dsb = QDoubleSpinBox(parent)
        dsb.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        #Set ranges
        dsb.setMinimum(float(c.minimum))
        dsb.setMaximum(float(c.maximum))

        return dsb

    def format_column_value(self, value):
        #Format double to string
        if not value is None:
            return str(value)

        return ''

DoubleWidgetFactory.register()


class PercentWidgetFactory(DoubleWidgetFactory):
    """
    Creates a widget for specifying percentage values.
    """
    COLUMN_TYPE_INFO = PercentColumn.TYPE_INFO
    _TYPE_PREFIX = 'psb_'

    @classmethod
    def _widget_configuration(cls, widget, c):
        #Add percentage suffix
        widget.setSuffix(' %')

PercentWidgetFactory.register()


class BooleanWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for YesNo column type.
    """
    COLUMN_TYPE_INFO = BooleanColumn.TYPE_INFO
    _TYPE_PREFIX = 'chb_'

    @classmethod
    def _create_widget(cls, c, parent):
        chb = QCheckBox(parent)
        chb.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        return chb

    def format_column_value(self, value):
        #Format to Yes/No
        if value is None:
            return ''

        if value:
            return QCoreApplication.translate('EntityBrowser', 'Yes')

        else:
            return QCoreApplication.translate('EntityBrowser', 'No')

BooleanWidgetFactory.register()


class RelatedEntityWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for ForeignKey column type.
    """
    COLUMN_TYPE_INFO = ForeignKeyColumn.TYPE_INFO
    _TYPE_PREFIX = 'rele_'

    def __init__(self, column):
        ColumnWidgetRegistry.__init__(self, column)

        self._parent_entity_cache = {}

        #Query all parent entities. Need for optimization
        p_entity = self._column.entity_relation.parent

        if p_entity is None:
            msg = QCoreApplication.translate(
                'RelatedEntityWidgetFactory',
                'The parent entity could not be determined. The input control '
                'will not be created.'
            )
            raise WidgetException(msg)

        self._p_entity_cls = entity_model(p_entity, entity_only=True)
        self._p_entity_obj = self._p_entity_cls()

        res = self._p_entity_obj.queryObject().filter().all()
        for r in res:
            self._parent_entity_cache[r.id] = r

    @classmethod
    def _create_widget(cls, c, parent):
        re_le = RelatedEntityLineEdit(c, parent)
        re_le.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        return re_le

    def format_column_value(self, value):
        """
        Sets the display based on the values of the display columns separated
        by single space.
        :param value: Primary key value fof the parent entity.
        :type value: int
        :return: Display extracted from the selected parent record.
        :rtype: str
        """
        if value in self._parent_entity_cache:
            rec = self._parent_entity_cache[value]

        else:
            #Query value
            rec = self._p_entity_obj.queryObject().filter(
                self._p_entity_cls.id == value
            ).first()

            if rec is None:
                return ''

            else:
                #Add to cache
                self._parent_entity_cache[rec.id] = rec

        return RelatedEntityLineEdit.process_display(self._column, rec)

RelatedEntityWidgetFactory.register()


class AdministrativeUnitWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for AdministrativeUnit column type.
    """
    COLUMN_TYPE_INFO = AdministrativeSpatialUnitColumn.TYPE_INFO
    _TYPE_PREFIX = 'aule_'

    def __init__(self, column):
        from PyQt4.QtGui import QMessageBox
        ColumnWidgetRegistry.__init__(self, column)

        self._aus_cache = {}

        #Query all admin units on initializing
        aus = self._column.entity.profile.administrative_spatial_unit
        self._aus_cls = entity_model(aus, entity_only=True)
        self._aus_obj = self._aus_cls()

        res = self._aus_obj.queryObject().filter().all()
        for r in res:
            self._aus_cache[r.id] = [r.name, r.code]

    @classmethod
    def _create_widget(cls, c, parent):
        aule = AdministrativeUnitLineEdit(c, parent)
        aule.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        return aule

    def format_column_value(self, value):
        """
        Extracts the admin unit name and code from the primary key.
        :param value: Primary key value for the administrative unit.
        :type value: int
        :return: Name and code corresponding to the given id.
        :rtype: str
        """
        if value in self._aus_cache:
            nc = self._aus_cache[value]
            name, code = nc[0], nc[1]

        else:
            #Query value
            res = self._aus_obj.queryObject().filter(
                self._aus_cls.id == value
            ).first()

            if res is None:
                return ''

            else:
                #Add result to the cache
                self._aus_cache[res.id] = res
                name, code = res.name, res.code

        if code:
            name = u'{0} ({1})'.format(name, code)

        return name

AdministrativeUnitWidgetFactory.register()


class LookupWidgetFactory(ColumnWidgetRegistry):
    """
    Widget factory for Lookup column type.
    """
    COLUMN_TYPE_INFO = LookupColumn.TYPE_INFO
    _TYPE_PREFIX = 'cbo_'

    def __init__(self, column):
        ColumnWidgetRegistry.__init__(self, column)

        self._lookups = {}

        #Query all lookups on initializing so as to reduce db roundtrips
        lookup = self._column.value_list
        lk_cls = entity_model(lookup, entity_only=True)
        lk_obj = lk_cls()
        res = lk_obj.queryObject().filter().all()

        for r in res:
            self._lookups[r.id] = [r.value, r.code]

    def lookups(self):
        """
        :return: Returns a collection indexed by the row id in the database.
        Each item in the collection contains a list where the value is the
        first item and code is the second.
        :rtype: dict
        """
        return self._lookups

    def code_value(self, id):
        """
        Searches for a the code value list based on the specified row id.
        :param id: Row id of the code value in the lookup.
        :type id: int
        :return: A tuple containing the value and code in the given row id,
        otherwise None.
        :rtype: tuple
        """
        if id in self._lookups:
            item = self._lookups[id]
            return item[0], item[1]

        return None

    @classmethod
    def _create_widget(cls, c, parent):
        cbo = QComboBox(parent)
        cbo.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        #Create a new instance of the class so that we can get the ids
        cls_obj = cls(c)
        lookups = cls_obj.lookups()
        cbo.addItem('', None)
        #Populate combobox
        for id, cd_val in lookups.iteritems():
            cbo.addItem(cd_val[0], id)

        return cbo

    def format_column_value(self, value):
        """
        Extracts the lookup value and code from the primary key.
        :param value: Primary key value for the lookup.
        :type value: int
        :return: Lookup value and code corresponding to the given id.
        :rtype: str
        """
        cd_val = self.code_value(value)

        if cd_val is None:
            return ''

        lk_val, lk_code = cd_val[0], cd_val[1]
        if lk_code:
            lk_val = u'{0} ({1})'.format(lk_val, lk_code)

        return lk_val


LookupWidgetFactory.register()


class MultipleSelectWidgetFactory(LookupWidgetFactory):
    """
    Widget factory for multiple column type.
    """
    COLUMN_TYPE_INFO = MultipleSelectColumn.TYPE_INFO
    _TYPE_PREFIX = 'mstv_'
    SEPARATOR = '; '

    @classmethod
    def _create_widget(cls, c, parent):
        mstv = MultipleSelectTreeView(c, parent)
        mstv.setObjectName(u'{0}_{1}'.format(cls._TYPE_PREFIX, c.name))

        return mstv

    def format_column_value(self, value):
        """
        Display values of the user selection. Lookup values will be separated
        by a semi-colon
        :param value: List containing lookup objects.
        :type value: list
        :return: Selected user values separated by the given separator.
        :rtype: str
        """
        if len(value) == 0:
            return ''

        #Get list of selected lookup values
        selection = []
        for lk in value:
            selection.append(lk.value)

        return self.SEPARATOR.join(selection)

MultipleSelectWidgetFactory.register()
