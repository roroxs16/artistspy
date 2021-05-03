from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from base64 import b64encode
from collections import OrderedDict
import json
from types import SimpleNamespace

# mysql+pymysql://{usuarioBDD}:{contrasena}@{IPBDD}/{nombre}
# HAY QUE CAMBIAR EL LINK DE LA BASE DE DATOS CUANDO HAGAS DEPLOY
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/flaskmysql'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
ma = Marshmallow(app)


class Artist(db.Model):
    id = db.Column(db.String(255), primary_key=True)  # base64
    name = db.Column(db.String(60))
    age = db.Column(db.Integer)
    albums = db.Column(db.Text)
    tracks = db.Column(db.Text)  # https://url/artists/id
    _self = db.Column("self", db.Text)  # https://url/artists/id

    def __init__(self, id, name, age, albums, tracks, _self):
        self.id = id
        self.name = name
        self.age = age
        self.albums = albums
        self.tracks = tracks
        self._self = _self


class Album(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    artist_id = db.Column(db.String(255), db.ForeignKey(
        'artist.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.Text)
    genre = db.Column(db.Text)
    artist = db.Column(db.Text)
    tracks = db.Column(db.Text)
    _self = db.Column("self", db.Text)

    def __init__(self, id, artist_id, name, genre, artist, tracks, _self):
        self.id = id
        self.name = name
        self.artist_id = artist_id
        self.genre = genre
        self.artist = artist
        self.tracks = tracks
        self._self = _self


class Track(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    album_id = db.Column(db.String(255), db.ForeignKey(
        'album.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.Text)
    duration = db.Column(db.Float)
    times_played = db.Column(db.Integer)
    artist = db.Column(db.Text)
    album = db.Column(db.Text)
    _self = db.Column("self", db.Text)

    def __init__(self, id, album_id, name, duration, times_played, artist, album, _self):
        self.id = id
        self.name = name
        self.album_id = album_id
        self.duration = duration
        self.times_played = times_played
        self.artist = artist
        self.album = album
        self._self = _self


db.create_all()


class ArtistSchema(ma.Schema):
    class Meta:
        fields = ('name', 'age', 'albums', 'tracks', '_self')


artist_schema = ArtistSchema()
artists_schema = ArtistSchema(many=True)


class AlbumSchema(ma.Schema):
    class Meta:
        fields = ('name', 'genre', 'artist', 'tracks', '_self')


album_schema = AlbumSchema()
albums_schema = AlbumSchema(many=True)


class TrackSchema(ma.Schema):
    class Meta:
        fields = ('name', 'duration', 'times_played', 'artist', 'album', '_self')


track_schema = TrackSchema()
tracks_schema = TrackSchema(many=True)

# artistas


@app.route('/artists', methods=['POST'])
def createArtist():
    # encoded = b64encode(string.encode()).decode('utf-8')

    if type(request.json['name']) is not str or type(request.json['age']) is not int:
       return 'Campos con valores invalidos', 400

    if (request.json['name'] == None or request.json['name'] == "") or request.json['age'] == None or request.json['age'] == 0:
       return 'Uno o los dos campos estan vacios', 400

    name = request.json['name']
    nameEncoded = b64encode(name.encode()).decode('utf-8')[:22]
    id = nameEncoded
    age = request.json['age']

    if Artist.query.get(id):
        artist = Artist.query.get(id)
        result = artist_schema.dump(artist)
        return artist_schema.jsonify(result), 409

    albums = request.url + "/" + nameEncoded + "/albums"
    tracks = request.url + "/" + nameEncoded + "/tracks"
    _self = request.url + "/" + nameEncoded

    new_artist = Artist(id, name, age, albums, tracks, _self)
    db.session.add(new_artist)
    db.session.commit()
    return artist_schema.jsonify(new_artist), 201


@app.route('/artists', methods=['GET'])
def getAllArtists():

    all_artists = Artist.query.all()

    if all_artists is None:
        return 'No hay registros de artistas con el id solicitado', 404

    result = artists_schema.dump(all_artists)
    return jsonify(result), 200


@app.route('/artists/<id>', methods=['GET'])
def getArtist(id):
    artist = Artist.query.get(id)

    if artist is None:
        return 'No hay registros de artistas con el id solicitado', 404

    result = artist_schema.dump(artist)
    return artist_schema.jsonify(result), 200


@app.route('/artists/<id>', methods=['DELETE'])
def deletArtist(id):

    artist = Artist.query.get(id)

    if artist is None:
       return 'No hay registros de artistas con el id solicitado', 404

    db.session.delete(artist)
    db.session.commit()

    return 'Artista eliminado', 204


@app.route('/artists/<id>/albums/play', methods=['PUT'])
def playArtistsTracks(id):
    artist = Artist.query.get(id)
    albums = Album.query.filter_by(artist_id=id).all()

    if artist is None:
       return 'No hay registros de artistas con el id solicitado', 404

    if albums is None:
       return 'No hay registros del albums con el id solicitado', 404

    for album in albums:
        playAlbumsTrack(album.id)

    return 'todas las canciones del artistas fueron reproducidas', 200

# albums


@app.route('/artists/<idArtist>/albums', methods=['POST'])
def createAlbum(idArtist):

    artistFound = Artist.query.get(idArtist)
    if artistFound is None:
       return 'No hay registros de artistas con el id solicitado', 422

    if type(request.json['name']) is not str or type(request.json['genre']) is not str:
       return 'Campos con valores invalidos', 400

    if (request.json['name'] == None or request.json['name'] == "") or request.json['genre'] == None or request.json['genre'] == "":
       return 'Uno o los dos campos estan vacios', 400

    # nota mental cuando se haga el deploy cambiar por el link del deploy
    link = 'http://localhost:5000/albums'

    name = request.json['name']

    artist_id = artistFound.id

    stringToCode = name+':'+idArtist
    nameEncoded = b64encode(stringToCode.encode()).decode('utf-8')[:22]

    id = nameEncoded

    if Album.query.get(id):
        album = Album.query.get(id)
        result = album_schema.dump(album)
        return album_schema.jsonify(result), 409

    genre = request.json['genre']

    artist = artistFound._self  # link del artista

    tracks = link + "/" + id + "/tracks"

    _self = link + "/" + id

    new_album = Album(id, artist_id, name, genre, artist, tracks, _self)
    db.session.add(new_album)
    db.session.commit()
    return album_schema.jsonify(new_album), 201


@app.route('/albums', methods=['GET'])
def getAllAlbums():
    allAlbums = Album.query.all()

    if allAlbums is None:
        return 'No hay registros de albums', 404

    result = albums_schema.dump(allAlbums)
    return jsonify(result), 200


@app.route('/albums/<id>', methods=['GET'])
def getAlbum(id):
    album = Album.query.get(id)

    if album is None:
        return 'No hay registros de album con el id solicitado', 404

    result = album_schema.dump(album)
    return album_schema.jsonify(result), 200


@app.route('/artists/<idArtist>/albums', methods=['GET'])
def getArtistAlbums(idArtist):
    artistFound = Artist.query.get(idArtist)

    if artistFound is None:
        return 'No hay registros del artista con el id solicitado', 404

    albums = Album.query.filter_by(artist_id=idArtist).all()

    if albums is None:
        return 'No hay registros del album con el id solicitado', 404

    result = albums_schema.dump(albums)
    return jsonify(result), 200


@app.route('/albums/<id>', methods=['DELETE'])
def deletAlbums(id):
    album = Album.query.get(id)

    if album is None:
        return 'No hay registros del album con el id solicitado', 404

    db.session.delete(album)
    db.session.commit()

    return 'Album eliminado', 204


@app.route('/albums/<id>/tracks/play', methods=['PUT'])
def playAlbumsTrack(id):
    album = Album.query.get(id)

    if album is None:
        return 'No hay registros del album con el id solicitado', 404

    tracks = Track.query.filter_by(album_id=id).all()

    if tracks is None:
        return 'El album no pose canciones', 404

    for track in tracks:
        track.times_played += 1
        db.session.add(track)
        db.session.commit()

    return 'canciones del album reproducidas', 200

# tracks

@app.route('/albums/<albumId>/tracks', methods=['POST'])
def createTrack(albumId):

    if type(request.json['name']) is not str or type(request.json['duration']) is not float:
       return 'Campos con valores invalidos', 400

    if (request.json['name'] == None or request.json['name'] == "") or request.json['duration'] == None:
       return 'Uno o los dos campos estan vacios', 400

    # nota mental cuando se haga el deploy cambiar por el link del deploy
    link = 'http://localhost:5000/tracks'

    albumFound = Album.query.get(albumId)

    if albumFound is None:
        return 'No hay registros del album con el id solicitado', 422

    artistFound = Artist.query.get(albumFound.artist_id)

    if artistFound is None:
        return 'El album no posee artista', 422

    name = request.json['name']
    album_id = albumFound.id

    stringToCode = name+':'+album_id
    nameEncoded = b64encode(stringToCode.encode()).decode('utf-8')[:22]

    id = nameEncoded

    if Track.query.get(id):
        track = Track.query.get(id)
        result = track_schema.dump(track)
        return track_schema.jsonify(result), 409

    duration = request.json['duration']
    times_played = 0
    album = albumFound._self
    artist = artistFound._self
    _self = link + "/" + id

    new_track = Track(id, album_id, name, duration,
                      times_played, artist, album, _self)

    db.session.add(new_track)
    db.session.commit()
    return track_schema.jsonify(new_track), 201


@app.route('/tracks', methods=['GET'])
def getAllTracks():
    allTracks = Track.query.all()

    if allTracks is None:
      return 'No hay registros de pistas con', 404

    result = tracks_schema.dump(allTracks)
    return jsonify(result), 200


@app.route('/tracks/<id>', methods=['GET'])
def getTrack(id):
    track = Track.query.get(id)

    if track is None:
      return 'No hay registros de pistas con el id solicitado', 404

    result = track_schema.dump(track)
    return track_schema.jsonify(result), 200

@app.route('/artists/<artistId>/tracks', methods = ['GET'])
def getAllTracksOfArtist(artistId):
    
    artist = Artist.query.get(artistId)

    if artist is None:
      return 'No existe artista', 404

    tracksList = []

    albums = Album.query.filter_by(artist_id=artistId).all()

    if albums is None:
      return 'No existen albums con el id del artista', 404
    
    for album in albums:
        tracks = Track.query.filter_by(album_id=album.id).all()
        tracksList.extend(tracks)
    
    if tracksList is None:
      return 'El artista no tiene canciones', 404

    result = tracks_schema.dump(tracksList)
    return jsonify(result), 200


@app.route('/albums/<albumId>/tracks', methods = ['GET'])
def getTracksAlbums(albumId):
    albumFound = Album.query.get(albumId)

    if albumFound is None:
      return 'No existen albumes con el id solicitado', 404

    tracks = Track.query.filter_by(album_id=albumId).all()

    if tracks is None:
      return 'No existen asociadas al album', 404

    result = tracks_schema.dump(tracks)
    return jsonify(result), 200

@app.route('/tracks/<id>', methods = ['DELETE'])
def deletTrack(id):
    track = Track.query.get(id)

    if track is None:
      return 'No existen canciones con el id solicitado', 404

    db.session.delete(track)
    db.session.commit()

    return 'Track eliminado', 204

@app.route('/tracks/<id>/play', methods = ['PUT'])
def playTrack(id):
    track = Track.query.get(id)

    if track is None:
      return 'No existen canciones con el id solicitado', 404

    track.times_played += 1
    db.session.add(track)
    db.session.commit()

    return 'Cancion reproducida', 200

if __name__ == "__main__":
    app.run(debug=True)
