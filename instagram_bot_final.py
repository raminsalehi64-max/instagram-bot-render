import io
import pandas as pd
import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
import asyncio

# ============ تنظیمات شما ============
TELEGRAM_BOT_TOKEN = "8495725535:AAFEfTgqtnB1F5Qn5vdreDd6Z6JpTBDaHKg"
GEMINI_API_KEY = "AIzaSyC2DlIw2gf2hXbg07IY_4T1PSQ0SVFjkHc"
# ====================================

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# --- تابع تنظیم دستورات منو ---
async def set_bot_commands(app: Application):
    """تنظیم دستورات منوی بات"""
    try:
        commands = [
            BotCommand("start", "شروع کار با بات"),
            BotCommand("help", "راهنمایی استفاده"),
            BotCommand("analyze", "تحلیل داده‌ها")
        ]
        await app.bot.set_my_commands(commands)
        print("✅ منوی بات تنظیم شد")
    except Exception as e:
        print(f"⚠️ خطا در تنظیم منو: {e}")

# --- بقیه توابع بدون تغییر (همان کد قبلی) ---
def extract_dashboard_sections(df):
    """استخراج بخش‌های مختلف از داشبورد"""
    sections = []
    
    for idx, row in df.iterrows():
        if 'DATE' in df.columns and pd.notna(row['DATE']):
            date_val = str(row['DATE']).strip()
            
            if not date_val.replace('.', '').isdigit():
                section_name = date_val
                section_data = {}
                
                month_cols = [col for col in df.columns if str(col).isdigit() and 1 <= int(str(col)) <= 12]
                
                for month in month_cols:
                    try:
                        if pd.notna(row[month]):
                            value = float(row[month])
                            section_data[f'ماه {month}'] = value
                    except:
                        pass
                
                if section_data:
                    sections.append({
                        'name': section_name,
                        'data': section_data,
                        'row_index': idx
                    })
    
    return sections

def format_data_for_display(df, sections):
    """قالب‌بندی داده‌ها برای نمایش به کاربر"""
    
    display_lines = ["📋 **نمایش کامل ساختار فایل**", "=" * 40, ""]
    
    display_lines.append(f"📁 **اطلاعات فایل:**")
    display_lines.append(f"• تعداد کل سطرها: {len(df)}")
    display_lines.append(f"• تعداد کل ستون‌ها: {len(df.columns)}")
    display_lines.append("")
    
    display_lines.append(f"🔤 **لیست ستون‌ها:**")
    for i, col in enumerate(df.columns, 1):
        display_lines.append(f"{i:2d}. '{col}' (نوع: {df[col].dtype})")
    display_lines.append("")
    
    display_lines.append(f"🔍 **بخش‌های شناسایی‌شده:** {len(sections)} بخش")
    for i, section in enumerate(sections, 1):
        display_lines.append(f"{i}. **{section['name']}** - سطر {section['row_index'] + 1}")
        
        month_display = []
        for month_name, value in section['data'].items():
            month_display.append(f"{month_name}: {value:,.0f}")
        
        if month_display:
            display_lines.append(f"   📊 {', '.join(month_display[:4])}" + 
                               ("..." if len(month_display) > 4 else ""))
    display_lines.append("")
    
    display_lines.append("📊 **جزئیات هر بخش:**")
    display_lines.append("-" * 40)
    
    for section in sections:
        display_lines.append(f"\n**{section['name']}**")
        display_lines.append(f"ردیف در فایل: {section['row_index'] + 1}")
        display_lines.append("مقادیر ماهانه:")
        
        months_sorted = sorted(section['data'].items(), 
                             key=lambda x: int(x[0].replace('ماه ', '')))
        
        for month_name, value in months_sorted:
            display_lines.append(f"  {month_name}: {value:,.0f}")
        
        values = list(section['data'].values())
        if values:
            avg = sum(values) / len(values)
            max_val = max(values)
            min_val = min(values)
            display_lines.append(f"  📈 میانگین: {avg:,.0f}")
            display_lines.append(f"  🔼 بیشترین: {max_val:,.0f}")
            display_lines.append(f"  🔽 کمترین: {min_val:,.0f}")
    
    return "\n".join(display_lines)

def analyze_with_confirmation(df, sections):
    """تحلیل نهایی پس از تأیید کاربر"""
    
    summary_lines = ["خلاصه داشبورد شبکه‌های اجتماعی:", ""]
    
    for section in sections:
        summary_lines.append(f"بخش: {section['name']}")
        values = list(section['data'].values())
        
        if values:
            avg = sum(values) / len(values)
            max_val = max(values)
            min_val = min(values)
            growth = ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
            
            summary_lines.append(f"  - میانگین ۹ ماهه: {avg:,.0f}")
            summary_lines.append(f"  - رشد کل: {growth:+.1f}%")
            summary_lines.append(f"  - دامنه: {min_val:,.0f} تا {max_val:,.0f}")
            summary_lines.append("")
    
    summary = "\n".join(summary_lines)
    
    prompt = f"""
    تو یک تحلیلگر حرفه‌ای شبکه‌های اجتماعی هستی.
    
    داده‌های زیر از یک داشبورد اینستاگرام استخراج شده‌اند:
    
    {summary}
    
    لطفاً تحلیل جامعی ارائه بده:
    
    ۱. **ارزیابی کلی عملکرد:** وضعیت کلی حساب چگونه است؟
    ۲. **تحلیل بخش‌ها:** هر بخش (views, interaction, etc) چه می‌گوید؟
    ۳. **روندها:** چه الگوهای فصلی یا ماهانه مشاهده می‌شود؟
    ۴. **نقاط قوت و ضعف:** کدام بخش‌ها قوی/ضعیف هستند؟
    ۵. **پیشنهادات عملی:** ۳ اقدام مشخص برای بهبود
    
    پاسخ را به فارسی، با تیترهای واضح و حداکثر ۲۵ خط بنویس.
    """
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"⚠️ خطا در تحلیل: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 **بات نمایش و تحلیل داده‌های داشبورد**\n\n"
        "📎 فایل اکسل داشبورد شبکه‌های اجتماعی خود را بفرستید.\n\n"
        "📋 **مراحل کار:**\n"
        "۱. فایل را آپلود می‌کنید\n"
        "۲. کل ساختار و داده‌ها را می‌بینید\n"
        "۳. تأیید می‌کنید که داده‌ها درست استخراج شده\n"
        "۴. تحلیل حرفه‌ای دریافت می‌کنید\n\n"
        "✅ ابتدا یک فایل ارسال کنید...\n\n"
        "📝 **دستورات:**\n"
        "/start - شروع کار\n"
        "/help - راهنمایی\n"
        "/analyze - تحلیل (بعد از آپلود)"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور help"""
    await update.message.reply_text(
        "🆘 **راهنمای استفاده:**\n\n"
        "۱. فایل اکسل خود را بفرستید\n"
        "۲. داده‌ها را بررسی کنید\n"
        "۳. با دکمه '✅ بله' تأیید کنید\n"
        "۴. تحلیل را دریافت کنید\n\n"
        "📁 **قالب فایل:**\n"
        "• ستون DATE برای نام بخش‌ها\n"
        "• ستون‌های ۱-۹ برای داده‌های ماهانه\n"
        "• فرمت xlsx یا xls\n\n"
        "🔧 **پشتیبانی:** در صورت مشکل فایل جدید ارسال کنید"
    )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور analyze"""
    if 'df' not in context.user_data:
        await update.message.reply_text(
            "⚠️ ابتدا یک فایل اکسل ارسال کنید.\n"
            "بعد از آپلود فایل، می‌توانید از این دستور استفاده کنید."
        )
        return
    
    msg = await update.message.reply_text("🧠 در حال تحلیل حرفه‌ای...")
    
    try:
        df = context.user_data['df']
        sections = context.user_data['sections']
        file_name = context.user_data['file_name']
        
        analysis = analyze_with_confirmation(df, sections)
        
        await update.message.reply_text(
            f"📊 **تحلیل حرفه‌ای {file_name}**\n\n"
            f"{analysis}\n\n"
            f"✅ تحلیل کامل شد!"
        )
        
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text(f"❌ خطا در تحلیل: {str(e)}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document.file_name.endswith(('.xlsx', '.xls')):
        await update.message.reply_text("⚠️ فقط فایل اکسل ارسال کنید.")
        return
    
    msg = await update.message.reply_text("📥 دریافت فایل...")
    
    try:
        file = await update.message.document.get_file()
        file_bytes = io.BytesIO()
        await file.download_to_memory(file_bytes)
        file_bytes.seek(0)
        
        df = pd.read_excel(file_bytes)
        
        await msg.edit_text("🔍 در حال استخراج ساختار داده‌ها...")
        sections = extract_dashboard_sections(df)
        
        if not sections:
            await msg.edit_text("❌ نتوانستم بخش‌های داشبورد را شناسایی کنم.")
            return
        
        await msg.edit_text("📊 در حال آماده‌سازی نمایش داده‌ها...")
        data_display = format_data_for_display(df, sections)
        
        display_parts = data_display.split('\n')
        chunk_size = 40
        
        for i in range(0, len(display_parts), chunk_size):
            chunk = '\n'.join(display_parts[i:i + chunk_size])
            await update.message.reply_text(f"```\n{chunk}\n```", parse_mode='Markdown')
        
        await msg.edit_text("✅ نمایش داده‌ها کامل شد!")
        
        context.user_data['df'] = df
        context.user_data['sections'] = sections
        context.user_data['file_name'] = update.message.document.file_name
        
        confirm_keyboard = {
            'keyboard': [[{'text': '✅ بله، تحلیل کن'}, {'text': '❌ خیر، فایل جدید'}]],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        await update.message.reply_text(
            "🤔 **آیا داده‌های بالا به درستی استخراج شده‌اند؟**\n\n"
            "اگر همه بخش‌ها و مقادیر را درست می‌بینید، دکمه '✅ بله' را بزنید.\n"
            "در غیر این صورت '❌ خیر' را بزنید و فایل بهتری ارسال کنید.",
            reply_markup=confirm_keyboard
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ خطا: {str(e)[:200]}")
        logging.error(f"Error: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پاسخ کاربر"""
    user_text = update.message.text
    
    if user_text == '✅ بله، تحلیل کن':
        if 'df' not in context.user_data:
            await update.message.reply_text("⚠️ لطفاً ابتدا فایل ارسال کنید.")
            return
        
        msg = await update.message.reply_text("🧠 در حال تحلیل حرفه‌ای...")
        
        try:
            df = context.user_data['df']
            sections = context.user_data['sections']
            file_name = context.user_data['file_name']
            
            analysis = analyze_with_confirmation(df, sections)
            
            await update.message.reply_text(
                f"📊 **تحلیل حرفه‌ای {file_name}**\n\n"
                f"{analysis}\n\n"
                f"✅ تحلیل کامل شد!"
            )
            
            await msg.delete()
            
        except Exception as e:
            await msg.edit_text(f"❌ خطا در تحلیل: {str(e)}")
            
    elif user_text == '❌ خیر، فایل جدید':
        await update.message.reply_text(
            "🔁 لطفاً فایل اکسل جدیدی ارسال کنید.\n\n"
            "💡 **توصیه:**\n"
            "• مطمئن شوید ستون DATE حاوی نام بخش‌ها باشد\n"
            "• ستون‌های ۱ تا ۹ حاوی اعداد باشند\n"
            "• از فرمت استاندارد استفاده کنید"
        )
    else:
        await update.message.reply_text(
            "لطفاً از دکمه‌های زیر استفاده کنید یا فایل جدیدی ارسال کنید."
        )

def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # ایجاد اپلیکیشن
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ثبت هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("=" * 50)
    print("🤖 بات نمایش و تحلیل داده‌های داشبورد")
    print("✨ ابتدا داده‌ها را می‌بینید، سپس تحلیل می‌کنید")
    print("🔗 به تلگرام بروید و فایل خود را بفرستید")
    print("=" * 50)
    
    # تنظیم منو قبل از اجرای بات
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(set_bot_commands(app))
    except:
        print("⚠️ تنظیم منو انجام نشد (مشکل اتصال)")
    
    # اجرای بات
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
