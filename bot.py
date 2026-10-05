"""VAPE_CULT bot.
Запуск:  pip install -r requirements.txt
         export BOT_TOKEN="токен от @BotFather"
         export ADMIN_ID="твой числовой Telegram id (узнать у @userinfobot)"
         python bot.py
Товары и цены правятся в catalog.json."""
import json, os, logging
from telegram import (Update, InlineKeyboardButton as B, InlineKeyboardMarkup as M,
                      ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters, ContextTypes)

logging.basicConfig(level=logging.INFO)
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("BOT_TOKEN", "8934320161:AAEluJ3z1vQ7ZQB1Mgh6N_VArSll1PbuxRE")
ADMIN = int(os.environ.get("ADMIN_ID", "5743634736"))
CAT = json.load(open(os.path.join(HERE, "catalog.json"), encoding="utf-8"))["categories"]
SECTORS = [["Ботаника", "Рышкановка"], ["Центр", "Чеканы", "Буюканы"]]
HOME = "Что вас интересует? 👇"

def home_kb():
    return M([[B(c["title"], callback_data=f"c:{i}")] for i, c in enumerate(CAT)])

def cart_text(cart):
    lines = [f"• {x['name']}" + (f" ({x['opt']})" if x["opt"] else "") + f" — {x['price']} лей" for x in cart]
    return "\n".join(lines) + f"\n\nИтого: {sum(x['price'] for x in cart)} лей"

async def show(q, text, kb):
    try:
        if q.message.photo:
            await q.edit_message_caption(caption=text, reply_markup=kb)
        else:
            await q.edit_message_text(text, reply_markup=kb)
    except Exception:
        await q.message.reply_text(text, reply_markup=kb)

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data.clear(); c.user_data["cart"] = []
    with open(os.path.join(HERE, "welcome.jpg"), "rb") as f:
        await u.message.reply_photo(f, caption="Добро пожаловать в VAPE_CULT 💨\n\n" + HOME, reply_markup=home_kb())

async def cb(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; await q.answer()
    d = q.data.split(":"); cart = c.user_data.setdefault("cart", [])
    if d[0] == "home":
        await show(q, HOME, home_kb())
    elif d[0] == "c":
        ci = int(d[1]); cat = CAT[ci]
        rows = [[B(f"{it['name']} — {it['price']} лей", callback_data=f"i:{ci}:{ii}")] for ii, it in enumerate(cat["items"])]
        rows.append([B("⬅️ Назад", callback_data="home")])
        await show(q, cat["title"] + "\nВыберите товар:", M(rows))
    elif d[0] == "i":
        ci, ii = int(d[1]), int(d[2]); cat = CAT[ci]; it = cat["items"][ii]
        opts = it.get("options") or []
        if not opts:
            return await add(q, cart, it, "")
        btns = [B(o, callback_data=f"o:{ci}:{ii}:{oi}") for oi, o in enumerate(opts)]
        rows = [btns[k:k + 2] for k in range(0, len(btns), 2)] + [[B("⬅️ Назад", callback_data=f"c:{ci}")]]
        await show(q, f"{it['name']} — {it['price']} лей\nВыберите {cat['variant']}:", M(rows))
    elif d[0] == "o":
        ci, ii, oi = map(int, d[1:4]); it = CAT[ci]["items"][ii]
        await add(q, cart, it, it["options"][oi])
    elif d[0] == "clear":
        cart.clear(); await show(q, "Корзина очищена.\n\n" + HOME, home_kb())
    elif d[0] == "checkout":
        if not cart:
            return await q.answer("Корзина пуста", show_alert=True)
        c.user_data["await"] = True
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Отправить геолокацию", request_location=True)]] + SECTORS,
            resize_keyboard=True, one_time_keyboard=True)
        cap = ("📍 Скиньте геолокацию — где вам удобно встретиться сегодня.\n\n"
               "Как это сделать — смотрите на картинке: скрепка → Геопозиция → Отправить.\n"
               "Или просто нажмите кнопку «📍 Отправить геолокацию» внизу.\n\n"
               "Если не получается — выберите сектор кнопкой или напишите его: "
               "Ботаника, Рышкановка, Центр, Чеканы, Буюканы.")
        with open(os.path.join(HERE, "tutorial.png"), "rb") as f:
            await q.message.reply_photo(f, caption=cap, reply_markup=kb)

async def add(q, cart, it, opt):
    cart.append({"name": it["name"], "price": it["price"], "opt": opt})
    kb = M([[B("➕ Добавить ещё", callback_data="home")],
            [B("✅ Оформить заказ", callback_data="checkout")],
            [B("🗑 Очистить", callback_data="clear")]])
    await show(q, "✅ Добавлено!\n\nВаша корзина:\n" + cart_text(cart), kb)

async def place(u: Update, c: ContextTypes.DEFAULT_TYPE):
    m = u.message; cart = c.user_data.get("cart")
    if not c.user_data.get("await") or not cart:
        return await m.reply_text("Нажмите /start, чтобы сделать заказ 💨", reply_markup=ReplyKeyboardRemove())
    usr = m.from_user
    who = usr.full_name + (f" @{usr.username}" if usr.username else "")
    place_txt = "геолокация 👇" if m.location else m.text
    await c.bot.send_message(ADMIN, f"🆕 Новый заказ\n👤 {who}\n🔗 tg://user?id={usr.id}\n\n"
                                    f"{cart_text(cart)}\n\n📍 Место: {place_txt}")
    if m.location:
        await c.bot.send_location(ADMIN, m.location.latitude, m.location.longitude)
    c.user_data.clear()
    await m.reply_text("✅ Заказ принят! Скоро с вами свяжутся.\nЕщё что-то? Нажмите /start",
                       reply_markup=ReplyKeyboardRemove())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.LOCATION | (filters.TEXT & ~filters.COMMAND), place))
    app.run_polling()

if __name__ == "__main__":
    main()
