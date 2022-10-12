

class _excel_formats:
    @staticmethod
    def bold(self, workbook):
        bold = workbook.add_format({'bold': True})
        return bold

    @staticmethod
    def droga_company_header_format(self, workbook):
        merge_droga_header_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 25,
            'fg_color': 'yellow'})
        return merge_droga_header_format

    @staticmethod
    def droga_header_title_format(self, workbook):
        merge_droga_title_format = workbook.add_format({
            'bold': 0,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': 'gray'})
        return merge_droga_title_format