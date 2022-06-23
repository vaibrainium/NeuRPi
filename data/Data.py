import tables
from pprint import pformat
from abc import ABC


from pydantic import BaseModel, BaseSettings, PrivateAttr

class Autopilot_Type(BaseModel, ABC):
    """
    Root autopilot model for types
    """
    _logger: typing.Optional[Logger] = PrivateAttr()

    def _init_logger(self):
        from autopilot.utils.loggers import init_logger
        self._logger = init_logger(self)

    def __str__(self):
        return pformat(self.dict(), indent=2, compact=True)

class Data(Autopilot_Type):
    """
    The top-level container for Data.
    Subtypes will define more specific formats and uses of data, but this is the most general
    form used to represent the type and meaning of data.
    The Data class is not intended to contain individual fields, but collections of data that are collected
    as a unit, whether that be a video frame along with its timestamp and encoding, or a single trial of behavioral data.
    This class is also generally not intended to be used for the literal transport of data when performance is
    necessary: this class by default does type validation on instantiation that takes time (see the `construct <https://pydantic-docs.helpmanual.io/usage/models/#creating-models-without-validation>`_
    method for validation-less creation). It is usually more to specify the type, grouping, and annotation for
    a given unit of data -- though users should feel free to dump their data in a :class:`.Data` object if
    it is not particularly performance sensitive.
    """

class Table(Data):
    """
    Tabular data: each field will have multiple values -- in particular an equal number across fields.
    Used for trialwise data, and can be used to create pytables descriptions.
    .. todo::
        To make this usable as a live container of data, the fields need to be declared as Lists (eg. instead of just
        declaring something an ``int``, it must be specified as a ``List[int]`` to pass validation. We should expand this
        model to relax that constraint and effectively treat every field as containing a list of values.
    """

    @classmethod
    def to_pytables_description(cls) -> typing.Type[tables.IsDescription]:
        """
        Convert the fields of this table to a pytables description.
        See :func:`~.interfaces.tables.model_to_description`
        """
        from autopilot.data.interfaces.tables import model_to_description
        return model_to_description(cls)

    @classmethod
    def from_pytables_description(cls, description:typing.Type[tables.IsDescription]) -> 'Table':
        """
        Create an instance of a table from a pytables description
        See :func:`~.interfaces.tables.description_to_model`
        Args:
            description (:class:`tables.IsDescription`): A Pytables description
        """
        from autopilot.data.interfaces.tables import description_to_model
        return description_to_model(description, cls)

    def to_df(self) -> pd.DataFrame:
        """
        Create a dataframe from the lists of fields
        Returns:
            :class:`pandas.DataFrame`
        """
        return pd.DataFrame(self.dict())


class Trial_Data(Table):
    """
    Base class for declaring trial data.
    Tasks should subclass this and add any additional parameters that are needed.
    The subject class will then use this to create a table in the hdf5 file.
    See :attr:`.Nafc.TrialData` for an example
    """
    group: Optional[str] = Field(None, description="Path of the parent step group")
    session: int = Field(..., description="Current training session, increments every time the task is started")
    session_uuid: Optional[str] = Field(None, description="Each session gets a unique uuid, regardless of the session integer, to enable independent addressing of sessions when session numbers might overlap (eg. reassignment)")
    trial_num: int = Field(..., description="Trial data is grouped within, well, trials, which increase (rather than resetting) across sessions within a task",
                           datajoint={"key":True})

