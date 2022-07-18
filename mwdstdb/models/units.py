from functools import partial
from pydantic.json import custom_pydantic_encoder
from pint import UnitRegistry

u = UnitRegistry()

u.enable_contexts('Gaussian')

u.define('fraction = [] = frac')
u.define('percent = 1e-2 frac = pct')
u.define('ppm = 1e-6 fraction')
u.define('gn = 9.80665 m/s^2')


StorageUnitSystem = {
    'acceleration': 'm/s^2',
    'angle': 'deg',
    'density': 'g/ml',
    'diameter': 'mm',
    'length': 'm',
    'magind': 'nT',
    'mass': 'kg',
    'temperature': 'degC',
    'ratio': 'percent',
    'ratio_fine': 'fraction',
    'dls_interval': 30.,
    'gaxes': ('X', 'Y', 'Z'),
    'maxes': ('X', 'Y', 'Z'),
    'gaxesi': (False, False, False),
    'maxesi': (False, False, False)
}

CalculationUnitSystem = {
    'acceleration': 'm/s^2',
    'angle': 'rad',
    'density': 'kg/m^3',
    'diameter': 'm',
    'length': 'm',
    'magind': 'nT',
    'mass': 'kg',
    'temperature': 'degC',
    'ratio': 'fraction',
    'ratio_fine': 'fraction',
    'dls_interval': 30.,
    'gaxes': ('X', 'Y', 'Z'),
    'maxes': ('X', 'Y', 'Z'),
    'gaxesi': (False, False, False),
    'maxesi': (False, False, False)
}


class Unit:
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update({'type': 'number'})
    @classmethod
    def validate(cls, v):
        return cls(float(v))


def unit_category(cat: str):
    class UnitCategory(Unit):
        def __init__(self, val: float):
            self._value = val
        def value(self, us_from, us_to):
            return float(u.Quantity(self._value, us_from[cat]).m_as(us_to[cat]))
        def __eq__(self, other):
            if isinstance(other, self.__class__):
                return self._value == other._value
            else:
                return False
        def __ne__(self, other):
            return not self.__eq__(other)
        def __lt__(self, other):
            if isinstance(other, self.__class__):
                return self._value < other._value
            else:
                raise ValueError("Comparison between incomparable units")
        def __gt__(self, other):
            return other.__lt__(self)
        def __le__(self, other):
            return not self.__gt__(other)
        def __ge__(self, other):
            return not self.__lt__(other)
    return UnitCategory


Acceleration = unit_category('acceleration')
Angle = unit_category('angle')
Density = unit_category('density')
Diameter = unit_category('diameter')
Length = unit_category('length')
MagneticInduction = unit_category('magind')
Mass = unit_category('mass')
Ratio = unit_category('ratio')
FineRatio = unit_category('ratio_fine')
Temperature = unit_category('temperature')


def get_units_encoder(source_us, target_us, additional_encoders: dict = None):
    additional_encoders = {} if additional_encoders is None else additional_encoders
    return partial(custom_pydantic_encoder, {
        Unit: lambda v: v.value(source_us, target_us),
        **additional_encoders
    })

def get_unit_converters(source_us, target_us):
    return { Unit: lambda v: v.value(source_us, target_us) }




