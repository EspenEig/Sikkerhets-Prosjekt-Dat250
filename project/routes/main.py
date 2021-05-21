from flask import Flask,g, redirect, render_template, request,session, url_for, flash, Blueprint
from flask_login import login_required, current_user
from flask_admin import Admin
from ..models import User, Transaction, BankAccount, ModelView, Roles, db
import random
from sqlalchemy import desc, or_
from .auth import limiter

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.errorhandler(404)
def forbidden(e):
  return render_template('404.html'), 404

@main.route('/profile')
@login_required
def profile():
    kontoer=BankAccount.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', fornavn=current_user.fornavn, email =current_user.email, etternavn = current_user.etternavn, addresse = current_user.postAddresse, postkode = current_user.postKode, fylke = current_user.fylke, kjonn = current_user.kjonn, fodselsdato = current_user.fodselsdato, password = current_user.password, kontoer=kontoer )

@main.route('/profile', methods=['POST'])
@login_required
def profile_post():
    kontoer=BankAccount.query.filter_by(user_id=current_user.id).all()
    #Oppdatere data inne i profil
    #skal kunne hente data fra db, og sjekke opp mot data i Profil. 
    #Om data er annerledes, oppdater data
    fornavn = request.form.get('fornavn')
    etternavn = request.form.get('etternavn')
    email = request.form.get('email')
    postAddresse = request.form.get('postAddresse')
    postKode = request.form.get('postKode')
    fylke = request.form.get('fylke')
    kjonn = str(request.form.get('Kjonn'))
    fodselsdato = request.form.get('fodselsdato')
    user = User.query.filter_by(id=current_user.id).first()

    #Burde ikke kunne sette lik mail som allerede er i databasen
    user.email = email
    user.fornavn = fornavn
    user.etternavn = etternavn
    user.postAddresse = postAddresse
    user.postKode = postKode
    user.fylke = fylke
    user.kjonn = kjonn
    user.fodselsdato = fodselsdato

    db.session.commit()
    return render_template('profile.html', fornavn=current_user.fornavn, email =current_user.email, etternavn = current_user.etternavn, addresse = current_user.postAddresse, postkode = current_user.postKode, fylke = current_user.fylke, kjonn = current_user.kjonn, fodselsdato = current_user.fodselsdato, password = current_user.password, kontoer=kontoer)

@main.route('/overview')
@login_required
def overview():
    kontoer=BankAccount.query.filter_by(user_id=current_user.id).all()
    return render_template('overview.html', kontoer=kontoer)
    
@main.route('/account<int:kontonr>')
@login_required
def account(kontonr):
    kontoen = BankAccount.query.filter_by(kontonr=int(kontonr)).first()
    # Må sjekke om kontoen faktisk er current_user sin konto slik at
    # man ikke kan endre URLen og få tilgang til oversikten for andre kontoer
    if not kontoen or kontoen.user_id != current_user.id:
        flash("Du har ikke tilgang til denne kontoen")
        return redirect(url_for('main.overview'))
    brukskontoer = BankAccount.query.filter_by(user_id=current_user.id, kontotype="bruk").all()
    transaksjoner = Transaction.query.order_by(desc(Transaction.id)).filter(or_(Transaction.avsender==kontonr, Transaction.mottaker==kontonr)).all()
    
    saldoer = {}
    rest = 0
    for transaksjon in transaksjoner:
        resultat = format(kontoen.saldo + rest, ",")
        saldoer[transaksjon] = resultat.replace(",", " ")
        if transaksjon.mottaker == kontoen.kontonr:
            rest -= transaksjon.verdi
        if transaksjon.avsender == kontoen.kontonr:
            rest += transaksjon.verdi

    return render_template('account.html', konto=kontoen, brukskontoer=brukskontoer, transaksjoner=transaksjoner, saldoer=saldoer)

@main.route('/account<int:kontonr>', methods=['POST'])
def account_post(kontonr):
    laanet = BankAccount.query.filter_by(kontonr=int(kontonr)).first()
    avsender_kontonr = request.form['fra_konto']
    avsender_konto = BankAccount.query.filter_by(kontonr=int(avsender_kontonr)).first()
    
    try:
        pengesum = float(request.form["pengesum"])
    except:
        flash("Ugyldig sum")
        return redirect(url_for('main.account', kontonr=laanet.kontonr))

    if pengesum <= 0:
        flash("Ugyldig sum")
        return redirect(url_for('main.account', kontonr=laanet.kontonr))

    trans_type = "Nedbetaling"

    if abs(laanet.saldo) < pengesum:
        flash(f"Du kan maks nedbetale {laanet.__str__().strip('-')} kr")
        return redirect(url_for('main.account', kontonr=laanet.kontonr))

    if avsender_konto.saldo < pengesum or avsender_konto.saldo <= 0:
        flash("Du har ikke nok penger")
        return redirect(url_for('main.account', kontonr=laanet.kontonr))

    # Oppdater databasen
    avsender_konto.saldo -= pengesum
    laanet.saldo += pengesum
    transaksjon = Transaction(trans_type=trans_type, verdi=pengesum, avsender=avsender_konto.kontonr, mottaker=laanet.kontonr)
    db.session.add(transaksjon)
    db.session.commit()

    if laanet.saldo == 0:
        db.session.delete(laanet)
        db.session.commit()
        flash("Du har nedbetalt hele lånet")
        return redirect(url_for('main.overview'))
    else:
        resultat = format(pengesum, ",")
        resultat = resultat.replace(",", " ")
        flash(f"Vellykket nedbetaling på {resultat} kr av lånet")
        return redirect(url_for('main.account', kontonr=laanet.kontonr))

@main.route('/create_bank_account')
@login_required
def create_bank_account():
    return render_template('create_bank_account.html')

@main.route('/create_bank_account', methods=['POST'])
def create_bank_account_post():
    kontotype = request.form['kontotype']
    kontonavn = request.form['kontonavn']
    kontonummer = int(random.randint(1e7, 1e8))
    while BankAccount.query.filter_by(kontonr=kontonummer).first():
        kontonummer = int(random.randint(1e7, 1e8))

    new_account = BankAccount(kontonr = kontonummer, navn = kontonavn, kontotype = kontotype, saldo=int(0), user_id = current_user.id)
    db.session.add(new_account)
    db.session.commit()
    return redirect(url_for('main.overview'))

# Sletting av bank konto
@main.route('/delete_bank_account<int:kontonr>')
@login_required
def delete_bank_account(kontonr):
    kontoen = BankAccount.query.filter_by(kontonr=int(kontonr)).first()
    if BankAccount is not None: # Om bakkontoen finnes
        if kontoen.saldo == 0: # om saldo er null, den slettes.
            db.session.delete(kontoen)
            db.session.commit()
            flash('Kontoen er slettet.')
            return redirect(url_for('main.overview'))
        else:
            flash('Kontoen må være tom før den kan slettes.') # Om den ikke er tom, feilmelding
            return redirect(url_for('main.account', kontonr=kontoen.kontonr))

@main.route('/create_loan')
@login_required
def create_loan():
    kontoen = BankAccount.query.filter_by(user_id=current_user.id, kontotype="bruk").first()
    if not kontoen:
        flash('Du må opprette en brukskonto før du kan opprette en låneavtale!')
        return redirect(url_for('main.overview'))

    return render_template('create_loan.html')

@main.route('/create_loan', methods=['POST'])
def create_loan_post():
    kontoer=BankAccount.query.filter_by(user_id=current_user.id).all()
    kontonavn = request.form['kontotype']
    for konto in kontoer:
        if konto.navn == kontonavn:
            flash(f'Du kan kun ha ett aktivt {kontonavn}')
            return redirect(url_for('main.create_loan'))
    kontotype = "lån"
    verdi = int(request.form['laan_verdi'])
    kontonummer = int(random.randint(1e7, 1e8))
    while BankAccount.query.filter_by(kontonr=kontonummer).first():
        kontonummer = int(random.randint(1e7, 1e8))

    new_loan = BankAccount(kontonr = kontonummer, navn = kontonavn, kontotype = kontotype, saldo=-int(verdi), user_id = current_user.id)
    db.session.add(new_loan)

    kontoen = BankAccount.query.filter_by(user_id=current_user.id, kontotype="bruk").first()
    kontoen.saldo += verdi

    transaksjon = Transaction(trans_type="Lån", verdi=verdi, avsender=new_loan.kontonr, mottaker=kontoen.kontonr)
    db.session.add(transaksjon)
    db.session.commit()

    return redirect(url_for('main.overview'))

@main.route('/transaction')
@login_required
def transaction():
    bruker_kontoer = BankAccount.query.filter_by(user_id=current_user.id).all()
    alle_kontoer = BankAccount.query.all()
    andre_kontoer = {}
    for konto in alle_kontoer:
        if konto not in bruker_kontoer:
            bruker = User.query.filter_by(id=konto.user_id).first()
            andre_kontoer[konto] = bruker.fornavn + " " + bruker.etternavn

    return render_template('transaction.html', bruker_kontoer=bruker_kontoer, andre_kontoer=andre_kontoer)

@main.route('/transaction', methods=['POST'])
def transaction_post():
    if request.form["btn"] == "overfør":
        if request.form["fra_konto"] == "velg" or request.form["til_konto"] == "velg":
            flash("Ugyldig konto")
            return redirect(url_for('main.transaction'))
        avsender_kontonr = request.form["fra_konto"]
        mottaker_kontonr = request.form["til_konto"]
        trans_type = "Overføring"
        
    if request.form["btn"] == "betal":
        if request.form["avsender_konto"] == "velg" or request.form["mottaker_konto"] == "velg":
            flash("Ugyldig konto")
            return redirect(url_for('main.transaction'))
        avsender_kontonr = request.form["avsender_konto"]
        mottaker_kontonr = request.form["mottaker_konto"]
        trans_type = "Betaling"

    try:
        pengesum = float(request.form["pengesum"])
    except:
        flash("Ugyldig sum")
        return redirect(url_for('main.transaction'))

    if pengesum <= 0:
        flash("Ugyldig sum")
        return redirect(url_for('main.transaction'))

    avsender_konto = BankAccount.query.filter_by(kontonr=int(avsender_kontonr)).first()
    mottaker_konto = BankAccount.query.filter_by(kontonr=int(mottaker_kontonr)).first()

    if not BankAccount.query.filter_by(kontonr=int(mottaker_kontonr)).all():
        flash("Ugyldig konto")
        return redirect(url_for('main.transaction'))

    if avsender_konto == mottaker_konto:
        flash("Kontoene er like")
        return redirect(url_for('main.transaction'))

    if avsender_konto.saldo < pengesum or avsender_konto.saldo <= 0:
        flash("Du har ikke nok penger")
        return redirect(url_for('main.transaction'))

    # Oppdater databasen
    avsender_konto.saldo -= pengesum
    mottaker_konto.saldo += pengesum
    transaksjon = Transaction(trans_type=trans_type, verdi=pengesum, avsender=avsender_kontonr, mottaker=mottaker_kontonr)
    db.session.add(transaksjon)
    db.session.commit()
    return redirect(url_for('main.overview'))


@main.route('/support')
def support():
     return render_template('support.html')

@main.route('/support', methods=['POST'])
def support_post():
    return render_template('support.html')

