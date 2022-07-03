#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from psycopg2 import Timestamp
from forms import *
from config import SQLALCHEMY_DATABASE_URI, SECRET_KEY, SQLALCHEMY_TRACK_MODIFICATIONS
from array import array
from datetime import datetime
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = SECRET_KEY
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

#show table: describes the many-to-many relationship between venue and artists
class Show(db.Model):
  __tablename__ = 'show'

  venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), primary_key=True, nullable=False)
  artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), primary_key=True, nullable=False)
  start_time = db.Column(db.DateTime, nullable=False)
  artist = db.relationship('Artist', back_populates='venues')
  venue = db.relationship('Venue', back_populates='artists')
  
class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(120))
    artists = db.relationship('Show', cascade='all, delete', back_populates='venue')

class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(120))
    venues = db.relationship('Show', cascade='all, delete', back_populates='artist')

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  #First retrieve venue object, then sort all venues according to city and state
  venue = Venue.query.all()
  city_dict = {}
  for i in venue:
    if not i.city in city_dict:
      city_dict[i.city] = {}
    if not i.state in city_dict[i.city]:
      city_dict[i.city][i.state] = []
    city_dict[i.city][i.state].append(i)

  venue_list = []
  for city in city_dict:
    for state in city_dict[city]:
      venue_list.append({'city': city, 'state': state, 'venues': city_dict[city][state]})

  return render_template('pages/venues.html', areas=venue_list)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  response = {}
  search_term = request.form.get('search_term', '')
  venue = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).all()
 
  search_list = []
  for i in venue:
    search_list.append({'id':i.id, 'name': i.name, 'num_upcoming_shows': 0})
  response['data'] = search_list
  response['count'] = search_list.count
  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  #start with venue object
  venue = Venue.query.get(venue_id)
  #load the artist and show table corresponding to venue_id
  show = Show.query.join(Artist).filter(venue_id==Show.venue_id).all()
  past_shows = []
  upcoming_shows = []
  #organizing data
  for i in show:
    if i.start_time > datetime.now():
      show_info = {}
      show_info['artist_id'] = i.artist_id
      show_info['artist_name'] = i.artist.name
      show_info['artist_image_link'] = i.artist.image_link
      show_info['start_time'] = str(i.start_time)
      upcoming_shows.append(show_info)
    else:
      show_info = {}
      show_info['artist_id'] = i.artist_id
      show_info['artist_name'] = i.artist.name
      show_info['artist_image_link'] = i.artist.image_link
      show_info['start_time'] = str(i.start_time)
      past_shows.append(show_info)
  venue.past_shows = past_shows
  venue.upcoming_shows = upcoming_shows

  return render_template('pages/show_venue.html', venue=venue)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

#helper function to check phone number
def is_valid_phone(number):
    regex = re.compile('^\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})$')
    return regex.match(number)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

  error = None
  if not is_valid_phone(request.form['phone']):
    flash('Invalid phone number!')
    error = 'Invalid phone number'
  else:
    try:
      name = request.form['name']
      city = request.form['city']
      state = request.form['state']
      address = request.form['address']
      phone = request.form['phone']
      genres = request.form.getlist('genres')
      image_link = request.form['image_link']
      facebook_link = request.form['facebook_link']
      website_link = request.form['website_link']
      seeking_talent = request.form.get('seeking_talent')
      seeking_description = request.form['seeking_description']
      #Create venue object and add to database
      venue = Venue(name=name, city=city, state=state, address=address, phone=phone, genres=genres,
      image_link=image_link, facebook_link=facebook_link, website_link=website_link,
      seeking_description=seeking_description) 
      venue.seeking_talent = bool(seeking_talent)
      db.session.add(venue)
      db.session.commit()
      # on successful db insert, flash success
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be edited.')
      error = 'An error occurred. Venue ' + request.form['name'] + ' could not be edited.'
      db.session.rollback()
    finally:
      db.session.close()

  if error:
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form, error=error)
  else:
    return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False
  try:
    venue = Venue.query.get(venue_id)
    db.session.delete(venue)
    db.session.commit()
  except:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be deleted.')
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    return render_template('pages/show_venue.html', venue=venue)
  else:
    return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artist=Artist.query.all()
  return render_template('pages/artists.html', artists=artist)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  response = {}
  search_term = request.form.get('search_term', '')
  artist = Artist.query.filter(Artist.name.ilike('%' + search_term + '%')).all()
 
  search_list = []
  for i in artist:
    search_list.append({'id':i.id, 'name': i.name, 'num_upcoming_shows': 0})
  response['data'] = search_list
  response['count'] = search_list.count
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # start with artist object
  artist = Artist.query.get(artist_id)
  # search for shows with artist_id, and get venue info as well
  show = Show.query.join(Venue).filter(artist_id==Show.artist_id).all()
  past_shows = []
  upcoming_shows = []
  #organize data
  for i in show:
    if i.start_time > datetime.now():
      show_info = {}
      show_info['venue_id'] = i.venue_id
      show_info['venue_name'] = i.venue.name
      show_info['venue_image_link'] = i.venue.image_link
      show_info['start_time'] = str(i.start_time)
      upcoming_shows.append(show_info)
    else:
      show_info = {}
      show_info['venue_id'] = i.venue_id
      show_info['venue_name'] = i.venue.name
      show_info['venue_image_link'] = i.venue.image_link
      show_info['start_time'] = str(i.start_time)
      past_shows.append(show_info)
  artist.past_shows = past_shows
  artist.upcoming_shows = upcoming_shows

  return render_template('pages/show_artist.html', artist=artist)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  # populate form with fields from artist with ID <artist_id>
  artist = Artist.query.get(artist_id)
  form = ArtistForm(name=artist.name, city=artist.city, state=artist.state, phone=artist.phone, genres=artist.genres,
  website_link=artist.website_link, facebook_link=artist.facebook_link, seeking_venue=artist.seeking_venue,
  seeking_description=artist.seeking_description, image_link=artist.image_link)
 
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  error = None

  if not is_valid_phone(request.form['phone']):
    flash('Invalid phone number!')
    error = 'Invalid phone number'
  else:
    try:
      artist = Artist.query.get(artist_id)
      artist.name = request.form['name']
      artist.city = request.form['city']
      artist.state = request.form['state']
      artist.phone = request.form['phone']
      artist.image_link = request.form['image_link']
      artist.genres = request.form.getlist('genres')
      artist.facebook_link = request.form['facebook_link']
      artist.website_link = request.form['website_link']
      artist.seeking_venue = bool(request.form.get('seeking_venue'))
      artist.seeking_description = request.form['seeking_description']
      db.session.commit()
      flash('Artist ' + request.form['name'] + ' was successfully edited!')
    except:
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be edited.')
      error = 'An error occurred. Artist ' + request.form['name'] + ' could not be edited.'
      db.session.rollback()
    finally:
      db.session.close()

  if error:
    artist = Artist.query.get(artist_id)
    form = ArtistForm(name=artist.name, city=artist.city, state=artist.state, phone=artist.phone, genres=artist.genres,
    website_link=artist.website_link, facebook_link=artist.facebook_link, seeking_venue=artist.seeking_venue,
    seeking_description=artist.seeking_description, image_link=artist.image_link)
    return render_template('forms/edit_artist.html', form=form, artist=artist, error=error)
  else:
    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  # populate form with values from venue with ID <venue_id>
  venue = Venue.query.get(venue_id)
  form = VenueForm(name=venue.name, city=venue.city, state=venue.state, address=venue.address, phone=venue.phone, genres=venue.genres,
  website_link=venue.website_link, facebook_link=venue.facebook_link, seeking_talent=venue.seeking_talent,
  seeking_description=venue.seeking_description, image_link=venue.image_link)
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  error = None

  if not is_valid_phone(request.form['phone']):
    flash('Invalid phone number!')
    error = 'Invalid phone number'
  else:
    try:
      venue = Venue.query.get(venue_id)
      venue.name = request.form['name']
      venue.city = request.form['city']
      venue.state = request.form['state']
      venue.phone = request.form['phone']
      venue.image_link = request.form['image_link']
      venue.genres = request.form.getlist('genres')
      venue.facebook_link = request.form['facebook_link']
      venue.website_link = request.form['website_link']
      venue.seeking_talent = bool(request.form.get('seeking_talent'))
      venue.seeking_description = request.form['seeking_description']
      db.session.commit()
      flash('Venue ' + request.form['name'] + ' was successfully edited!')
    except:
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be edited.')
      error = 'An error occurred. Venue ' + request.form['name'] + ' could not be edited.'
      db.session.rollback()
    finally:
      db.session.close()

  if error:
    venue = Venue.query.get(venue_id)
    form = VenueForm(name=venue.name, city=venue.city, state=venue.state, address=venue.address, phone=venue.phone, genres=venue.genres,
    website_link=venue.website_link, facebook_link=venue.facebook_link, seeking_talent=venue.seeking_talent,
    seeking_description=venue.seeking_description, image_link=venue.image_link)
    return render_template('forms/edit_venue.html', form=form, venue=venue, error=error)
  else:
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # insert form data as a new Venue record in the db, instead
  # modify data to be the data object returned from db insertion
  error = None

  if not is_valid_phone(request.form['phone']):
    flash('Invalid phone number!')
    error = 'Invalid phone number'
  else:
    try:
      name = request.form['name']
      city = request.form['city']
      state = request.form['state']
      phone = request.form['phone']
      image_link = request.form['image_link']
      genres = request.form.getlist('genres')
      facebook_link = request.form['facebook_link']
      website_link = request.form['website_link']
      seeking_venue = request.form.get('seeking_venue')
      seeking_description = request.form['seeking_description']
      #Create venue object and add to database
      artist = Artist(name=name, city=city, state=state, phone=phone, image_link=image_link, genres=genres,
      facebook_link=facebook_link, website_link=website_link, seeking_description=seeking_description) 
      artist.seeking_venue = bool(seeking_venue)
      db.session.add(artist)
      db.session.commit()
      # on successful db insert, flash success
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
      db.session.rollback()
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
      error = 'An error occurred. Artist ' + request.form['name'] + ' could not be listed.'
    finally:
      db.session.close()

  # on unsuccessful db insert, flash an error instead.
  if error:
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form, error=error)
  else:
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  show = Show.query.join(Venue).join(Artist).all()
  show_data = []
  for i in show:
    show_data.append(
      {'venue_id': i.venue_id,
      'venue_name': i.venue.name,
      'artist_id': i.artist_id,
      'artist_name': i.artist.name,
      'artist_image_link': i.artist.image_link,
      'start_time': str(i.start_time)
      }
    )
  return render_template('pages/shows.html', shows=show_data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form

  artist_id = request.form['artist_id']
  venue_id = request.form['venue_id']
  start_time = request.form['start_time']

  #Create show object and add to database
  artist = Artist.query.get(artist_id)
  print(artist)
  venue = Venue.query.get(venue_id)
  print(venue)
  error = False

  if not artist:
    flash('An error occurred. Artist ID' + artist_id + ' does not exist.')
    error = True
  elif not venue:
    flash('An error occurred. Venue ID' + venue_id + ' does not exist.')
    error = True
  else:
    print('object exists')
    try:
      show = Show(artist=artist, venue=venue, start_time=start_time)
      venue.artists.append(show)
      db.session.add(show)
      flash('Show was successfully listed!')
      db.session.commit()
    except:
      flash('An error occurred. Show could not be listed.')
      error = True
      db.session.rollback()
    finally:
      db.session.close()
  
  # on unsuccessful db insert, flash an error instead.
  if error:
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)
  else:
    return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
