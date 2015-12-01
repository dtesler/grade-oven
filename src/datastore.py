import cStringIO
import os
import shutil
import tempfile

import leveldb


class DataStore(object):
  def __init__(self, dir_path=None):
    if dir_path is None:
      dir_path = tempfile.mkdtemp()
    self.db = leveldb.LevelDB(dir_path, paranoid_checks=True)


  def put(self, key, value):
    mods = leveldb.WriteBatch()
    partial_key = cStringIO.StringIO()
    for j, key_part in enumerate(key, 1):
      partial_key.write('\x00')
      len_partial = partial_key.tell()
      partial_key.seek(0)
      partial_key.write(chr(j))
      partial_key.seek(len_partial)
      partial_key.write(key_part)
      partial_key.seek(0)
      mods.Put(partial_key.read(), '')
    partial_key.seek(0)
    mods.Put(partial_key.read(), value)
    self.db.Write(mods)

  def get(self, key):
    real_key = cStringIO.StringIO()
    real_key.write(chr(len(key)))
    real_key.write('\x00'.join(key))
    real_key.seek(0)
    return self.db.Get(real_key.read())

  def get_all(self, key):
    real_key = cStringIO.StringIO()
    real_key.write(chr(len(key) + 1))
    real_key.write('\x00'.join(key))
    real_key.seek(0)
    start_key = real_key.read()
    real_key.write('\x01')
    real_key.seek(0)
    end_key = real_key.read()
    sub_keys = []
    for sub_key in self.db.RangeIter(start_key, end_key, include_value=False):
      sub_keys.append(sub_key.rsplit('\x00')[-1])
    return sub_keys

  def remove(self, key):
    real_key = cStringIO.StringIO()
    real_key.write(chr(len(key)))
    real_key.write('\x00'.join(key))
    real_key.seek(0)
    mods = leveldb.WriteBatch()
    for j in xrange(len(key), 256):
      real_key.seek(0)
      real_key.write(chr(j))
      real_key.seek(0)
      start_key = real_key.read()
      end_key = start_key + '\x01'
      found_keys = False
      for k in self.db.RangeIter(start_key, end_key, include_value=False):
        mods.Delete(k)
        found_keys = True
      if not found_keys:
        break
    self.db.Write(mods)


if __name__ == '__main__':
  key1 = ('courses', 'c++',    'assignments', 'homework 1')
  key2 = ('courses', 'c++',    'assignments', 'homework 2')
  key3 = ('courses', 'python', 'assignments', 'homework 1')
  temp_dir = tempfile.mkdtemp()
  try:
    store = DataStore(temp_dir)
    store.put(key1, 'c++ 1')
    store.put(key2, 'c++ 2')
    store.put(key3, 'python 1')
    assert set(store.get_all(('courses',))) == set(['c++', 'python'])
    assert store.get(key1) == 'c++ 1'
    assert store.get(key3) == 'python 1'
    store.remove(('courses', 'c++'))
    assert set(store.get_all(('courses',))) == set(['python'])
  finally:
    shutil.rmtree(temp_dir)