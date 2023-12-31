from hack import app, create_db, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from hack.forms import LoginForm, RegForm, UseResourceForm
from hack.models import User, Post, Like, Comment, Resource, Page, ResourceUsage, Message, UserSubscription
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4
from werkzeug.utils import secure_filename
import datetime
import requests
import openai
from dotenv import load_dotenv
from os import getenv
import stripe

load_dotenv()
stripe.api_key = 'sk_test_51O8JhiSHhRhBTwdEcLCCXkOXos3lSvIIFaxYlJyna5O6VClutnBp85IWSgwCDxYDmfNl054S95j49jLf6VYlc3nd00I90av8L9'
app.config['UPLOAD_FOLDER'] = 'hack/static/uploads'
create_db(app)
openai.api_key = getenv('OPENAI_API_KEY')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    # Get the logged-in user
    current_user = User.query.get(current_user.id)
    
    # Assuming the customer ID is stored in the User model
    customer_id = current_user.stripe_customer_id  # Retrieve Stripe customer ID from the database

    if customer_id:
        # Use Stripe Billing Portal to create a session for subscription cancellation
        stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=url_for('home', _external=True)  # Redirect user to home page after cancellation
        )
        return jsonify({'status': 'success', 'message': 'Subscription cancellation initiated. Redirecting to the billing portal...'})
    else:
        return jsonify({'status': 'error', 'message': 'Stripe customer ID not found.'})

@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    if request.args.get('success') == 'True':
        print('whoo niga')
        current_user.sub_plan = 'Pro'
        db.session.add(current_user)
        db.session.commit()
        flash('Payment successful.', 'success')
        return redirect(url_for('billing'))
    elif request.args.get('success') == 'False':
        flash('Payemnt cancelled.', 'error')
        return redirect(url_for('billing'))
    if request.method == 'POST':
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': 'price_1O8Jk8SHhRhBTwdERBjxB7sz',
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url='https://astral-0idp.onrender.com/billing?success=True',
            cancel_url='https://astral-0idp.onrender.com/billing?success=False',
        )
        return redirect(session.url, code=303)

    return render_template('upgrade.html', user=current_user)

@app.route('/cancel', methods=['POST'])
@login_required
def cancel():
    current_user.sub_plan = 'Free'
    db.session.add(current_user)
    db.session.commit()
    flash('Plan cancelled successfully.', 'success')
    return redirect(url_for('billing'))

@app.route('/repository')
def repository():
    posts=Post.query.all()
    return render_template('repository.html', posts=posts)

@app.route('/dashboard')
@login_required
def dashboard():
    resource_usage_data = ResourceUsage.query.filter_by(user_id=current_user.id).all()
    dates = [data.date.strftime('%Y-%m-%d') for data in resource_usage_data]
    usages = [data.usage for data in resource_usage_data]
    low_resources = [resource for resource in current_user.resources if resource.quantity <= 5]
    print(low_resources)
    return render_template('dashboard.html', dates=dates, usages=usages, low_resources=low_resources)

@app.route('/dashboard/add-resources', methods=['GET', 'POST'])
@login_required
def add_resources():
    if request.method == 'POST':
        resource_names = request.form.getlist('resource-name[]')
        resource_quantities = request.form.getlist('resource-quantity[]')
        for name, quantity in zip(resource_names, resource_quantities):
            if name and quantity:
                resource = Resource(name=name, quantity=int(quantity), user=current_user.id)
                db.session.add(resource)
                db.session.commit()
        flash('Resources added successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_resources.html')

@app.route('/dashboard/resource/<id>', methods=['GET', 'POST'])
@login_required
def resource(id):
    resource = Resource.query.filter_by(id=id, user=current_user.id).first_or_404()
    form = UseResourceForm()
    resource_usage_data = ResourceUsage.query.filter_by(resource_id=resource.id, user_id=current_user.id).all()
    dates = [data.date.strftime('%Y-%m-%d') for data in resource_usage_data]
    usages = [data.usage for data in resource_usage_data]
    if form.validate_on_submit():
        procured_quantity = form.qty.data
        resource.quantity += procured_quantity
        db.session.add(resource)
        db.session.commit()    
        flash('Quantity updated successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('resource.html', resource=resource, resource_usage_data=resource_usage_data, dates=dates, usages=usages, form=form)

@app.route('/contribute-data', methods=['GET', 'POST'])
@login_required
def contribute():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_type = request.form['category']
        image = request.files['image']
        filename = str(uuid4()) + '_' + secure_filename(image.filename)
        image.save(app.config['UPLOAD_FOLDER'] + '/' + filename)
        new_post = Post(title=title, content=content, post_type=post_type, image=filename, author=current_user.username)
        db.session.add(new_post)
        db.session.commit()
        flash('Thanks for contributing to our repository.', 'success')
        return redirect(url_for('repository'))
    return render_template('contribute.html')

@app.route('/dashboard/resource/<id>/use-resource/', methods=['GET', 'POST'])
def use_resource(id):
    resource = Resource.query.filter_by(id=id).first_or_404()
    form = UseResourceForm()
    if form.validate_on_submit():
        usage = form.qty.data
        new_usage = ResourceUsage(usage=usage, resource_id=resource.id, user_id=current_user.id)
        if usage > resource.quantity:
            flash(f"You don't have this much {resource.name.lower()}!", 'error')
            return redirect(url_for('dashboard'))
        if usage == resource.quantity:
            db.session.delete(resource)
            db.session.commit()
            flash(f"You've used up all of your {resource.name.lower()}!", 'error')
            return redirect(url_for('dashboard'))
        resource.quantity -= usage
        db.session.add(resource)
        db.session.add(new_usage)
        db.session.commit()
        flash('Usage recorded successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('use_resource.html', resource=resource, form=form)

@app.route('/posts/<id>')
def post(id):
    post = Post.query.filter_by(id=id).first_or_404()
    has_user_liked = False if not current_user.is_authenticated else True if Like.query.filter_by(user_id=current_user.id, post_id=post.id).first() else False
    return render_template('post.html', post=post, has_user_liked=has_user_liked)

@app.route('/addcomment/<id>', methods=['POST'])
@login_required
def add_comment(id):
    post = Post.query.filter_by(id=id).first_or_404()
    comment = request.get_json()['comment']
    new_comment = Comment(content=comment, author=current_user.username, post=post.id)
    db.session.add(post)
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/likepost/<id>', methods=['POST'])
@login_required
def like_post(id):
    try:
        post = Post.query.filter_by(id=id).first_or_404()
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)
        db.session.add(post)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(e)
        return jsonify({'success': False})

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    form = RegForm()
    mess = ''
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Account already exists.', 'error')
        else:
            new_user = User(email=email, username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Account created successfully', 'success')
            if request.args.get('next'):
                print(request.args.get('next'))
                return redirect(request.args.get('next'))
            return redirect(url_for('home'))
    return render_template('reg.html', form=form, mess=mess)

@app.route('/get_map_data', methods=['GET'])
def get_map_data():
    # Example map data
    # Replace this with your map data
    map_data = {"type":"FeatureCollection","features":[{"type":"Feature","id":"values","roadWidth":8,"towerRadius":7.6,"wallThickness":7.6,"generator":"mfcg","version":"0.9.2"},{"type":"Polygon","id":"earth","coordinates":[[[-1096.204,103.952],[-993.832,211.739],[-975.944,415.435],[-858.918,504.295],[-817.764,628.08],[-808.507,634.315],[-812.933,950.027],[-585.359,963.539],[-497.625,1127.858],[-470.8,1205.458],[-253.648,1004.275],[-19.356,1235.674],[31.719,1490.521],[244.545,1231.837],[520.988,1157.818],[461.993,933.564],[705.494,883.915],[957.619,1024.34],[983.657,787.555],[892.318,630.036],[871.761,514.108],[877.474,507.156],[1319.445,372.12],[927.971,272.715],[887.275,202.468],[733.017,208.07],[634.91,316.735],[541.038,330.901],[444.162,212.736],[377.493,194.979],[326.362,159.899],[314.199,46.762],[233.093,34.466],[152.833,14.664],[123.218,-51.984],[163.607,-107.484],[154.273,-221.166],[245.604,-281.765],[221.197,-395.229],[238.818,-450.468],[391.529,-454.674],[484.2,-518.274],[480.863,-650.335],[631.376,-770.468],[778.35,-827.233],[756.261,-1058.814],[714.523,-1092.704],[399.196,-994.926],[256.977,-1103.42],[215.969,-1184.361],[171.142,-1201.235],[15.97,-1109.449],[-98.604,-1084.143],[-181.697,-1128.965],[-310.993,-990.207],[-581.057,-1184.922],[-624.149,-838.269],[-651.206,-787.432],[-1041.22,-769.387],[-898.335,-577.212],[-926.349,-288.829],[-920.723,-284.378],[-968.557,-62.227],[-1093.768,18.654]]]},{"type":"GeometryCollection","id":"roads","geometries":[{"type":"LineString","width":8,"coordinates":[[-34.297,-11.726],[-72.352,-33.509],[-123.258,-0.882],[-206.18,25.419],[-313.79,30.361],[-375.091,50.854],[-457.544,96.065],[-626.538,113.612],[-761.37,163.642],[-838.461,181.859],[-993.832,211.739]]},{"type":"LineString","width":8,"coordinates":[[-21.702,29.031],[-26.343,66.353],[-13.975,107.2],[-17.248,176.388],[-28.465,254.453],[-53.261,318.818],[-73.395,406.048],[-109.412,454.206],[-132.507,532.345],[-111.286,672.814],[-139.079,813.948],[-97.112,901.853],[-22.458,1013.307],[-19.356,1235.674]]},{"type":"LineString","width":8,"coordinates":[[26.544,-43.194],[14.35,-91.119],[7.728,-135.612],[-18.452,-180.986],[-10.616,-244.93],[22.585,-358.009],[40.001,-462.935],[36.823,-534.534],[46.239,-647.143],[13.629,-763.769],[-46.497,-806.662],[-112.325,-851.061],[-98.604,-1084.143]]},{"type":"LineString","width":8,"coordinates":[[-72.352,-33.509],[-95.052,-104.537],[-160.342,-98.794]]}]},{"type":"GeometryCollection","id":"walls","geometries":[{"type":"Polygon","width":7.6,"coordinates":[[[-182.046,80.287],[-120.232,147.456],[-17.248,176.388],[72.119,185.97],[142.9,163.294],[188.298,107.634],[233.093,34.466],[152.833,14.664],[123.218,-51.984],[163.607,-107.484],[154.273,-221.166],[63.117,-235.548],[-10.616,-244.93],[-96.675,-206.823],[-173.613,-171.161],[-160.342,-98.794],[-193.705,-13.69],[-206.18,25.419]]]},{"type":"Polygon","width":7.6,"coordinates":[[[-160.342,-98.794],[-173.613,-171.161],[-212.153,-175.935],[-263.435,-114.832],[-251.415,-61.917],[-193.705,-13.69]]]}]},{"type":"GeometryCollection","id":"rivers","geometries":[]},{"type":"GeometryCollection","id":"planks","geometries":[{"type":"LineString","width":4.8,"coordinates":[[169.662,18.816],[177.327,-12.253]]},{"type":"LineString","width":4.8,"coordinates":[[192.963,24.565],[200.628,-6.504]]},{"type":"LineString","width":4.8,"coordinates":[[216.264,30.314],[223.929,-0.755]]}]},{"type":"MultiPolygon","id":"buildings","coordinates":[[[[1.788,-79.891],[-11.205,-71.257],[-26.11,-61.354],[-39.82,-52.244],[-52.499,-43.819],[-42.658,-29.008],[-34.2,-16.279],[-21.521,-24.704],[-29.979,-37.433],[-16.269,-46.543],[-1.364,-56.447],[7.094,-43.718],[20.087,-52.351],[11.629,-65.08]]],[[[-187.802,-71.49],[-182.957,-83.848],[-176.488,-100.351],[-192.08,-106.463],[-205.674,-111.792],[-219.12,-117.063],[-225.589,-100.56],[-230.434,-88.202],[-237.37,-70.509],[-223.924,-65.239],[-216.988,-82.931],[-212.144,-95.289],[-198.549,-89.96],[-203.394,-77.602]]],[[[-191.425,366.964],[-181.672,350.78],[-191.349,344.949],[-201.102,361.133]]],[[[-184.582,378.691],[-180.117,382.852],[-176.166,386.534],[-172.069,382.137],[-166.898,386.956],[-162.886,382.651],[-168.057,377.832],[-172.009,374.15],[-176.473,369.989],[-180.485,374.295]]],[[[173.659,335.518],[180.196,335.99],[180.523,331.463],[181.037,324.35],[174.499,323.878],[168.518,323.447],[162.289,322.997],[161.776,330.109],[168.005,330.559],[173.986,330.991]]],[[[-110.653,537.763],[-109.66,544.335],[-105.064,543.641],[-103.513,553.907],[-98.964,553.22],[-100.515,542.954],[-101.508,536.381],[-106.057,537.069]]],[[[287.198,609.905],[290.48,606.71],[296.027,601.311],[292.728,597.922],[287.181,603.321],[283.709,599.754],[280.427,602.949],[275.134,608.101],[278.606,611.668],[283.899,606.516]]],[[[362.238,435.53],[358.687,440.551],[355.163,445.533],[351.581,450.597],[355.638,453.467],[359.221,448.403],[362.616,450.804],[366.139,445.823],[362.744,443.421],[366.296,438.4]]],[[[82.509,480.714],[80.229,486.957],[84.596,488.552],[81.035,498.304],[85.357,499.882],[88.917,490.129],[91.197,483.886],[86.875,482.308]]],[[[287.209,626.638],[291.644,630.899],[296.044,635.126],[300.518,639.423],[303.96,635.839],[299.487,631.542],[302.368,628.543],[297.968,624.316],[295.087,627.315],[290.652,623.054]]],[[[-34.445,778.485],[-40.221,780.652],[-37.891,786.863],[-47.582,790.499],[-45.981,794.766],[-36.29,791.13],[-30.514,788.962],[-32.115,784.695]]],[[[196.911,782.414],[189.58,787.974],[192.117,791.32],[195.225,795.419],[202.557,789.859],[208.029,785.709],[204.921,781.611],[199.449,785.76]]]]},{"type":"MultiPolygon","id":"prisms","coordinates":[[[[1.421,-14.93],[-2.954,-12.667],[-0.763,-8.43],[3.613,-10.693]]]]},{"type":"MultiPolygon","id":"squares","coordinates":[[[[34.297,11.726],[26.544,-43.194],[-34.297,-11.726],[-21.702,29.031]]]]},{"type":"MultiPolygon","id":"greens","coordinates":[]},{"type":"MultiPolygon","id":"fields","coordinates":[[[[-186.828,268.817],[-158.584,246.283],[-155.046,239.81],[-152.243,212.709],[-155.73,207.835],[-194.41,198.958],[-201.161,200.867],[-234.535,233.673],[-234.164,238.845],[-193.178,268.944]]],[[[-134.138,264.163],[-149.248,253.952],[-155.689,254.207],[-240.096,321.551],[-240.296,326.773],[-196.416,367.663],[-191.425,366.964],[-132.888,269.829]]],[[[-81.591,349.071],[-72.627,310.236],[-75.042,304.099],[-120.872,273.128],[-126.251,274.314],[-154.61,321.374],[-152.935,326.219],[-86.23,351.548]]],[[[-162.936,335.189],[-185.444,372.538],[-184.582,378.691],[-125.235,433.994],[-119.913,433.518],[-95.072,400.303],[-91.777,393.202],[-85.206,364.734],[-88.046,359.416],[-157.132,333.183]]],[[[-42.57,364.984],[-52.169,406.57],[-49.396,412.053],[-12.542,427.967],[-7.284,425.881],[9.308,387.456],[7.221,382.198],[-37.998,362.672]]],[[[15.651,372.767],[41.025,314.004],[39.466,307.859],[-8.212,270.376],[-12.795,271.636],[-31.886,321.193],[-34.224,328.824],[-38.942,349.264],[-36.169,354.748],[10.393,374.853]]],[[[2.147,434.31],[73.708,465.21],[77.538,462.799],[82.159,345.545],[79.172,339.076],[52.26,317.918],[47.53,319.119],[0.06,429.052]]],[[[90.323,341.53],[89.044,373.996],[92.883,378.151],[171.912,381.265],[176.63,377.488],[182.013,348.128],[178.745,343.906],[94.47,337.821]]],[[[184.907,332.344],[194.317,281.018],[191.131,276.229],[127.752,262.377],[122.193,265.167],[94.606,326.047],[96.945,329.979],[180.196,335.99]]],[[[189.515,442.865],[244.52,394.881],[243.537,392.094],[181.791,389.661],[178.409,393.456],[185.886,441.542]]],[[[165.651,389.025],[92.568,386.144],[88.414,389.984],[85.47,464.679],[89.311,468.578],[158.086,466.892],[165.099,464.164],[176.358,454.343],[178.757,447.761],[170.263,393.135]]],[[[-214.723,498.433],[-161.448,527.871],[-155.658,529.673],[-152.234,525.705],[-128.819,446.482],[-130.611,439.919],[-164.881,407.985],[-169.742,408.759],[-216.289,492.997]]],[[[-268.772,536.197],[-176.919,530.899],[-176.426,528.734],[-243.473,491.686],[-248.909,493.253],[-270.831,532.926]]],[[[-32.635,642.727],[17.524,626.225],[22.695,621.217],[45.64,558.37],[43.093,553.811],[-25.589,539.771],[-29.771,542.961],[-36.171,639.985]]],[[[-40.747,587.817],[-37.682,541.343],[-41.337,536.551],[-104.112,523.718],[-109.165,526.753],[-110.117,529.972],[-110.653,537.763],[-100.914,602.225],[-96.429,605.238],[-44.898,592.75]]],[[[-98.519,618.076],[-92.449,658.254],[-88.052,660.959],[-48.429,647.923],[-44.366,642.682],[-41.826,604.165],[-45.45,601.115],[-95.229,613.179]]],[[[-21.43,532.455],[45.867,546.213],[51.158,543.257],[74.723,478.712],[72.423,473.369],[10.02,446.423],[4.976,448.595],[-23.977,527.897]]],[[[-4.681,440.075],[-52.553,419.404],[-58.621,421.022],[-88.127,460.475],[-91.656,467.514],[-104.622,511.38],[-101.836,516.018],[-37.193,529.233],[-31.902,526.277],[-2.381,445.419]]],[[[238.769,564.201],[276.637,614.649],[281.905,615.058],[348.061,550.661],[347.873,545.288],[299.901,504.714],[293.98,504.921],[239.234,558.212]]],[[[287.656,494.358],[217.089,434.674],[211.02,434.721],[172.07,468.699],[171.457,474.527],[229.125,551.352],[234.392,551.761],[287.843,499.731]]],[[[235.944,412.979],[223.147,424.142],[223.187,429.355],[303.737,497.481],[309.101,496.799],[335.386,459.639],[334.07,454.684],[242.583,412.039]]],[[[362.238,435.53],[315.232,501.984],[315.977,507.833],[353.633,539.681],[359.553,539.474],[412.837,487.607],[412.913,481.951],[367.338,435.131]]],[[[75.744,672.725],[132.508,728.183],[138.518,728.512],[185.815,691.463],[186.497,685.848],[138.032,623.977],[132.416,623.295],[76.032,667.463]]],[[[128.165,611.382],[106.316,583.489],[100.165,581.898],[39.284,607.641],[34.228,612.956],[30.431,623.355],[31.92,629.908],[64.249,661.494],[70.259,661.823],[127.483,616.997]]],[[[222.914,556.404],[210.268,539.557],[204.182,537.916],[115.167,575.555],[113.95,580.261],[143.804,618.373],[149.42,619.055],[222.167,562.07]]],[[[153.671,630.969],[192.795,680.914],[198.41,681.597],[269.87,625.62],[270.617,619.955],[232.52,569.202],[226.97,568.47],[154.353,625.353]]],[[[82.509,480.714],[40.721,595.17],[43.034,597.37],[111.576,568.388],[113.941,563.053],[85.199,480.733]]],[[[126.327,562.15],[199.233,531.323],[200.516,526.566],[164.065,478.006],[157.665,474.905],[96.197,476.412],[93.517,480.286],[121.325,559.931]]],[[[-211.265,540.893],[-273.628,544.49],[-276.411,548.533],[-246.69,642.103],[-241.591,644.976],[-214.14,638.344],[-210.129,633.406],[-207.395,544.661]]],[[[-198.3,634.517],[-144.115,621.425],[-140.825,616.531],[-152.164,541.475],[-156.755,537.75],[-195.26,539.97],[-199.377,544.199],[-202.065,631.458]]],[[[-140.491,713.469],[-133.166,676.269],[-132.99,668.389],[-138.43,632.381],[-142.916,629.366],[-230.116,650.434],[-233.065,655.261],[-214.78,730.942],[-209.951,733.896],[-145.154,718.328]]],[[[413.554,498.074],[373.812,536.758],[373.373,542.728],[419.772,603.509],[425.378,604.262],[469.1,570.886],[469.853,565.279],[418.847,498.463]]],[[[320.095,589.048],[287.19,621.077],[287.209,626.638],[358.113,694.753],[363.864,694.734],[394.214,665.191],[394.29,659.535],[325.751,589.124]]],[[[405.679,654.031],[427.249,633.034],[427.688,627.065],[367.599,548.349],[362.306,547.959],[331.56,577.887],[331.484,583.544],[400.022,653.955]]],[[[467.63,679.388],[437.432,639.829],[432.139,639.439],[369.637,700.279],[369.655,705.84],[397.728,732.808],[403.792,733.152],[466.878,684.995]]],[[[25.837,789.859],[16.314,763.711],[11.2,761.358],[-49.912,784.289],[-52.186,789.413],[-41.586,816.205],[-36.389,818.469],[23.481,795.073]]],[[[-47.733,774.927],[8.462,753.841],[10.838,748.677],[-24.167,652.572],[-29.336,650.063],[-85.705,668.609],[-89.637,670.531],[-88.4,674.963],[-52.847,772.573]]],[[[-93.53,690.301],[-114.406,796.309],[-111.434,798.828],[-62.714,780.548],[-60.338,775.384],[-91.388,690.135]]],[[[88.54,696.411],[26.219,635.522],[19.558,633.977],[-14.133,645.062],[-16.564,650.07],[10.513,724.411],[15.641,726.801],[87.643,700.575]]],[[[126.252,733.256],[100.61,708.203],[93.991,706.777],[18.379,734.317],[15.989,739.445],[30.283,778.69],[35.264,780.729],[125.502,737.771]]],[[[310.42,660.029],[281.188,631.947],[275.154,631.643],[210.495,682.293],[209.812,687.908],[245.606,733.602],[250.719,733.751],[310.658,665.8]]],[[[340.601,765.254],[381.163,733.48],[381.427,728.243],[321.963,671.119],[316.433,671.347],[280.274,712.339],[280.637,717.974],[334.442,765.086]]],[[[269.69,724.338],[255.736,740.157],[255.557,746.305],[294.629,796.184],[300.244,796.867],[327.893,775.208],[328.033,770.107],[275.345,723.973]]],[[[237.212,840.173],[280.409,797.447],[280.786,791.486],[247.539,749.043],[241.885,748.311],[189.58,787.974],[189.088,793.346],[231.672,840.031]]]]},{"type":"MultiPoint","id":"trees","coordinates":[]},{"type":"GeometryCollection","id":"districts","geometries":[{"type":"Polygon","name":"OldTown","coordinates":[[[-173.613,-171.161],[-160.342,-98.794],[-95.052,-104.537],[-72.352,-33.509],[-123.258,-0.882],[-85.664,70.748],[-26.343,66.353],[-13.975,107.2],[-17.248,176.388],[72.119,185.97],[142.9,163.294],[91.177,101.801],[91.115,56.209],[58.224,32.193],[123.218,-51.984],[163.607,-107.484],[154.273,-221.166],[63.117,-235.548],[-10.616,-244.93],[-96.675,-206.823]]]},{"type":"Polygon","name":"HarbourWard","coordinates":[[[58.224,32.193],[91.115,56.209],[91.177,101.801],[142.9,163.294],[188.298,107.634],[233.093,34.466],[152.833,14.664],[123.218,-51.984]]]},{"type":"Polygon","name":"ElmChapel","coordinates":[[[-13.975,107.2],[-26.343,66.353],[-85.664,70.748],[-120.232,147.456],[-17.248,176.388]]]},{"type":"Polygon","name":"NorthQuarter","coordinates":[[[-156.035,249.366],[-53.261,318.818],[-28.465,254.453],[86.199,344.601],[125.532,257.798],[72.119,185.97],[-17.248,176.388],[-120.232,147.456],[-151.417,204.721]]]},{"type":"Polygon","name":"Woolgate","coordinates":[[[-313.79,30.361],[-182.046,80.287],[-120.232,147.456],[-85.664,70.748],[-123.258,-0.882],[-72.352,-33.509],[-95.052,-104.537],[-160.342,-98.794],[-193.705,-13.69],[-251.415,-61.917]]]},{"type":"Polygon","name":"Castle","coordinates":[[[-160.342,-98.794],[-173.613,-171.161],[-212.153,-175.935],[-263.435,-114.832],[-251.415,-61.917],[-193.705,-13.69]]]},{"type":"Polygon","name":"SouthWard","coordinates":[[[-96.675,-206.823],[-10.616,-244.93],[63.117,-235.548],[60.812,-322.369],[22.585,-358.009],[-94.323,-338.606]]]}]},{"type":"MultiPolygon","id":"water","coordinates":[[[[123.218,-51.984],[152.833,14.664],[233.093,34.466],[314.199,46.762],[326.362,159.899],[377.493,194.979],[444.162,212.736],[541.038,330.901],[634.91,316.735],[733.017,208.07],[887.275,202.468],[1015.842,180.754],[1408.553,237.359],[1275.606,60.604],[1173.81,-198.352],[1358.609,-439.706],[1145.357,-601.368],[1031.456,-703.676],[881.857,-766.118],[778.35,-827.233],[631.376,-770.468],[480.863,-650.335],[484.2,-518.274],[391.529,-454.674],[238.818,-450.468],[221.197,-395.229],[245.604,-281.765],[154.273,-221.166],[163.607,-107.484]]]]}]}
    return jsonify(map_data)

@app.route('/navigation')
def navigation():
    return render_template('navigation.html')

@app.route('/guru')
@login_required
def guru():
    if current_user.sub_plan == 'Free':
        flash('You need to upgrade to the pro plan to access this feature.', 'error')
        return redirect(url_for('pricing'))
    messages = Message.query.filter_by(user=current_user.id).all()
    return render_template('guru2.html', messages=messages)

@app.route('/ask_question', methods=['POST'])
@login_required
def ask_question():
    messages = [{"role": "system", "content" : "You are the Nuxeland guru, a large language model trained by the development Team of Astral. Nuxeland is a mystical land where individuals get teleported to upon saying specific phrases. It is full of both desirable and undesirable creatures. Astral helps users stuck in Nuxeland to escape. It provides various features such as inventory management and analysis, navigation and a knowledge repository. Answer as concisely and simply as possible."}
    ]
    user_question = request.form['user_question']
    message = Message(content=request.form['user_question'], role='user', user=current_user.id)
    db.session.add(message)
    db.session.commit()
    messages.append({"role": "user", "content": user_question})


    # Use the OpenAI GPT-3 API to get a response
    completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo", 
    messages = messages)
    response = Message(content=completion['choices'][0]['message']['content'], role='ai', user=current_user.id)
    db.session.add(response)
    db.session.commit()

    print(response.content)

    return jsonify({'response': completion['choices'][0]['message']['content']})



@app.route('/find_route', methods=['POST'])
def find_route():
    start = request.json.get('start')
    end = request.json.get('end')

    url = "https://graphhopper.com/api/1/route"
    params = {
        "point": [f"{start['lat']},{start['lng']}", f"{end['lat']},{end['lng']}"],
        "vehicle": "car",
        "points_encoded": False,
        "key": "4c11e19e-7647-4133-af1e-d773887d1deb"  # Replace with your actual API key
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        route_data = response.json()
        return jsonify(route_data)
    else:
        return jsonify({"error": "Route not found"})
    
@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/journal', methods=['GET', 'POST'])
@login_required
def journal():
    if request.method == 'POST':
        content = request.form['content']
        page = Page(content=content, user=current_user.id)
        db.session.add(page)
        db.session.add(current_user)
        db.session.commit()
        flash('Successfully filled today\'s journal.', 'success')
        return redirect(url_for('journal'))
    print(datetime.datetime.now().strftime('%b %d'))
    already_written = Page.query.filter_by(user=current_user.id, created_at=datetime.datetime.now().strftime('%b %d')).first()
    return render_template('journal.html', already_written=already_written)

@app.route('/journal/page/<id>', methods=['GET', 'POST'])
@login_required
def page(id):
    page = Page.query.filter_by(id=id, user=current_user.id).first_or_404()
    return render_template('page.html', page=page)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    mess=''
    print(request.args.get('next'))
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email not found.', 'error')
        else:
            if check_password_hash(user.password, password):
                login_user(user, remember=True)
                if request.args.get('next'):
                    print(request.args.get('next'))
                    return redirect(request.args.get('next'))
                return redirect(url_for('home'))
            else:
                flash('Incorrect password.', 'error')
    return render_template('login.html', mess=mess, form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=6969)
