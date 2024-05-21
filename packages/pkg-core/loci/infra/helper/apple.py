# -----------------------------------------------------------------------
# Thanks to the source code from https://github.com/threeplanetssoftware/apple_cloud_notes_parser/blob/master/lib/AppleNotesEmbeddedTable.rb
# This file was generated by OpenAI's GPT-4
# -----------------------------------------------------------------------
import itertools
from typing import List, Dict

from ...domain import NoteAttachmentTableCell
from ...protobuf import MergableDataProto, MergeableDataObjectEntry, MergeableDataObjectMap, DictionaryElement


class AppleNotesTableConstructor:
    LEFT_TO_RIGHT_DIRECTION = "CRTableColumnDirectionLeftToRight"
    RIGHT_TO_LEFT_DIRECTION = "CRTableColumnDirectionRightToLeft"

    TABLE_ROOT_KRY = "com.apple.notes.ICTable"
    TABLE_DIRECTION_KEY = "crTableColumnDirection"

    TABLE_ROW_KEY = "crRows"
    TABLE_COLUMN_KEY = "crColumns"
    TABLE_CELL_KEY = "cellColumns"

    reconstructed_table: List[NoteAttachmentTableCell] = []

    def __init__(self, mergable_data_proto: MergableDataProto):
        self.key_items: List[str] = []
        self.type_items: List[str] = []
        # self.row_items = []
        self.table_objects: List[MergeableDataObjectEntry] = []
        self.uuid_items: List[bytes] = []
        self.total_columns = 0
        self.row_indices: Dict[str, int] = {}
        self.column_indices: Dict[int, int] = {}
        self.table_direction = self.LEFT_TO_RIGHT_DIRECTION

        self._rebuild_table(mergable_data_proto)

    def __str__(self):
        string_to_add = " with cells: "
        for row in self.reconstructed_table:
            string_to_add += "\n"
            for column in row:
                string_to_add += f"\t{column}"
        return super().__str__() + string_to_add

    @classmethod
    def get_target_uuid_from_object_entry(cls, object_entry):
        return object_entry.custom_map.map_entry[0].value.unsigned_integer_value

    def parse_rows(self, object_entry):

        rows = object_entry.ordered_set.ordering

        row_indices = {self.uuid_items.index(attachment.uuid): idx for idx, attachment in enumerate(rows.array.attachment)}

        for element in rows.contents.element:
            key_object = self.get_target_uuid_from_object_entry(self.table_objects[element.key.object_index])
            value_object = self.get_target_uuid_from_object_entry(self.table_objects[element.value.object_index])
            if key_object not in row_indices:
                continue
            self.row_indices[value_object] = row_indices[key_object]

    def parse_columns(self, object_entry):

        columns = object_entry.ordered_set.ordering

        column_indices = {self.uuid_items.index(attachment.uuid): idx for idx, attachment in enumerate(columns.array.attachment)}

        for element in columns.contents.element:
            key_object = self.get_target_uuid_from_object_entry(self.table_objects[element.key.object_index])
            value_object = self.get_target_uuid_from_object_entry(self.table_objects[element.value.object_index])
            if key_object not in column_indices:
                continue
            self.column_indices[value_object] = column_indices[key_object]

    def get_cell_for_column_row(self, current_column: int, row: DictionaryElement) -> None | NoteAttachmentTableCell:
        current_row = self.get_target_uuid_from_object_entry(self.table_objects[row.key.object_index])

        target_cell = self.table_objects[row.value.object_index]

        r_idx = self.row_indices[current_row]
        c_idx = self.column_indices[current_column]

        if r_idx is None or c_idx is None:
            return None
        return NoteAttachmentTableCell(column = r_idx, row = c_idx, text = target_cell.note.note_text)

    def get_cell_for_column(self, column) -> List[NoteAttachmentTableCell]:
        current_column = self.get_target_uuid_from_object_entry(self.table_objects[column.key.object_index])
        target_dictionary_object = self.table_objects[column.value.object_index]

        cell_list = map(
            lambda row: self.get_cell_for_column_row(current_column, row),
            target_dictionary_object.dictionary.element
        )
        return [cell for cell in cell_list if cell is not None]

    def parse_table(self, custom_map: MergeableDataObjectMap):
        if not custom_map:
            return

        if self.type_items[custom_map.type] != self.TABLE_ROOT_KRY:
            return

        for map_entry in custom_map.map_entry:
            if self.key_items[map_entry.key] == self.TABLE_ROW_KEY:
                self.parse_rows(self.table_objects[map_entry.value.object_index])
            elif self.key_items[map_entry.key] == self.TABLE_COLUMN_KEY:
                self.parse_columns(self.table_objects[map_entry.value.object_index])

        cell_columns_to_parse = None
        for map_entry in custom_map.map_entry:
            if self.key_items[map_entry.key] == self.TABLE_CELL_KEY:
                cell_columns_to_parse = self.table_objects[map_entry.value.object_index]

        if len(self.row_indices) <= 0 or len(self.column_indices) <= 0 or not cell_columns_to_parse:
            return

        cell_element = cell_columns_to_parse.dictionary.element
        self.reconstructed_table = list(itertools.chain.from_iterable([self.get_cell_for_column(column) for column in cell_element]))

    def _rebuild_table(self, mergable_data_proto: MergableDataProto):

        object_data = mergable_data_proto.mergable_data_object.mergeable_data_object_data

        self.key_items = [key_item for key_item in object_data.mergeable_data_object_key_item]
        self.type_items = [type_item for type_item in object_data.mergeable_data_object_type_item]
        self.uuid_items = [uuid_item for uuid_item in object_data.mergeable_data_object_uuid_item]
        self.table_objects = [object_entry for object_entry in object_data.mergeable_data_object_entry]

        for object_entry in object_data.mergeable_data_object_entry:
            if not object_entry.custom_map or len(object_entry.custom_map.map_entry) == 0:
                continue

            key: int = object_entry.custom_map.map_entry[0].key
            value: str = object_entry.custom_map.map_entry[0].value.string_value

            if self.TABLE_DIRECTION_KEY == self.key_items[key - 1]:
                self.table_direction = value
                break

        for object_entry in object_data.mergeable_data_object_entry:
            if not object_entry.custom_map:
                continue

            if self.TABLE_ROOT_KRY == self.type_items[object_entry.custom_map.type]:
                # fount the table root.
                self.parse_table(object_entry.custom_map)

        # TODO: sort self.reconstructed_table by direction