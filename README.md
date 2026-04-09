# Charlie AI — English Lesson Engine

An EdTech AI service that orchestrates vocabulary mini-lessons for children aged 4-8.  
Charlie is a playful 8-year-old fox from London who teaches English words through guided conversation.

---

## Quick Start

```bash
# 1. Clone & enter the project
cd charlie-ai

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your Groq API key (free at https://console.groq.com)
cp .env.example .env
# Edit .env → set GROQ_API_KEY=gsk_...

# 5. Run the lesson
python main.py

# Or with custom words:
python main.py apple house tree
```

### Example Session

```
Charlie: Hi there! I'm Charlie the fox! Let's learn some fun words today! Yay!

Child:   hello!

Charlie: Oh wow, hello! Our first word is cat! A cat is a fluffy animal
        that goes meow! Can you say cat?

Child:   cat

Charlie: Yay! You said cat! Amazing!
        Next word is dog! A dog is a happy friend that goes woof! Can you say dog?

Child:   I like Spiderman

Charlie: Oh cool, Spiderman is awesome! But can you try saying dog for me?

Child:   dog!

Charlie: Woohoo! Dog! You're so good at this!
            ...
```