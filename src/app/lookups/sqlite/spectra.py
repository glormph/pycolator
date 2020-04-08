from app.lookups.sqlite.biosets import BioSetDB


class SpectraDB(BioSetDB):
    def add_tables(self):
        super().add_tables()
        self.create_tables(['mzml', 'ioninjtime', 'ionmob'])

    def store_mzmls(self, spectra, ioninj, ionmob):
        self.store_many(
            'INSERT INTO mzml(spectra_id, mzmlfile_id, scan_sid, charge, mz, '
            'retention_time) '
            'VALUES (?, ?, ?, ?, ?, ?)', spectra)
        self.store_many(
            'INSERT INTO ioninjtime(spectra_id, ion_injection_time) '
            'VALUES(?, ?)', ioninj)
        self.store_many(
            'INSERT INTO ionmob(spectra_id, ion_mobility) '
            'VALUES(?, ?)', ionmob)

    def index_mzml(self):
        self.index_column('spectra_id_index', 'mzml', 'spectra_id')
        self.index_column('mzmlfnid_mzml_index', 'mzml', 'mzmlfile_id')
        self.index_column('scan_index', 'mzml', 'scan_sid')
        self.index_column('specrt_index', 'mzml', 'retention_time')
        self.index_column('specmz_index', 'mzml', 'mz')

    def get_exp_spectra_data_rows(self):
        cursor = self.get_cursor()
        return cursor.execute('SELECT pr.rownr, bs.set_name, sp.retention_time, '
                              'sp.ion_injection_time '
                              'FROM psmrows AS pr '
                              'JOIN psms AS p USING(psm_id) '
                              'JOIN mzml AS sp USING(spectra_id) '
                              'JOIN mzmlfiles as mf USING(mzmlfile_id) '
                              'JOIN biosets AS bs USING(set_id) '
                              'ORDER BY pr.rownr')
