import streamlit as st
st.set_page_config(page_title="Living Pages", layout="wide", initial_sidebar_state="expanded")

import requests
import json
import random
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import time

class RelationshipLevel(Enum):
    HOSTILE = -2
    UNFRIENDLY = -1
    NEUTRAL = 0
    FRIENDLY = 1
    TRUSTED = 2
    ALLY = 3

@dataclass
class Character:
    name: str
    description: str
    relationship: RelationshipLevel = RelationshipLevel.NEUTRAL
    relationship_points: int = 0
    last_interaction: str = ""
    traits: List[str] = field(default_factory=list)
    
    def update_relationship(self, change: int):
        self.relationship_points = max(-10, min(10, self.relationship_points + change))
        if self.relationship_points <= -7:
            self.relationship = RelationshipLevel.HOSTILE
        elif self.relationship_points <= -3:
            self.relationship = RelationshipLevel.UNFRIENDLY
        elif self.relationship_points <= 2:
            self.relationship = RelationshipLevel.NEUTRAL
        elif self.relationship_points <= 6:
            self.relationship = RelationshipLevel.FRIENDLY
        elif self.relationship_points <= 9:
            self.relationship = RelationshipLevel.TRUSTED
        else:
            self.relationship = RelationshipLevel.ALLY

class WorldState:
    def __init__(self):
        self.characters: Dict[str, Character] = {}
        self.locations = ["Village Square", "Dark Forest", "Mystic Caverns", "Abandoned Tower"]
        self.current_location = "Village Square"
        self.time_of_day = "morning"
        self.quests = {}
        
    def add_character(self, name: str, description: str, traits: List[str] = None):
        if name not in self.characters:
            self.characters[name] = Character(name=name, description=description, traits=traits or [])
    
    def get_character(self, name: str) -> Optional[Character]:
        return self.characters.get(name)
    
    def update_character_relationship(self, name: str, change: int):
        if name in self.characters:
            self.characters[name].update_relationship(change)
    
    def to_dict(self):
        return {
            "characters": {name: {
                "relationship": char.relationship.name,
                "relationship_points": char.relationship_points,
                "last_interaction": char.last_interaction,
                "traits": char.traits
            } for name, char in self.characters.items()},
            "current_location": self.current_location,
            "time_of_day": self.time_of_day
        }

# Custom CSS
st.markdown("""
    <style>
    .story-container { background-color: #2d2d2d; color: #f0f0f0; padding: 20px; border-radius: 10px; margin-bottom: 20px; max-height: 400px; overflow-y: auto; font-family: 'Georgia', serif; line-height: 1.6; }
    .choice-btn { margin: 5px; min-width: 200px; }
    .header { color: #4CAF50; }
    .user-choice { color: #64B5F6; font-style: italic; }
    .narrative-event { color: #FFA000; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Query Gemini free-tier model
def query_model(prompt: str, system_prompt: str = None) -> str:
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n{prompt}"
    
    url = "https://generativelanguage.googleapis.com/v1beta2/models/gemini-2.5-flash-lite:generateMessage"
    headers = {"Content-Type": "application/json"}
    data = {"prompt": {"messages": [{"author": "user", "content": full_prompt}]}}
    
    try:
        response = requests.post(url, headers=headers, params={"key": st.secrets["API_KEY"]}, json=data)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]
    except Exception as e:
        return f"Error querying Gemini: {str(e)}"

def generate_suggested_actions(story_context: str) -> List[str]:
    system_prompt = "You are an AI that suggests 3-4 possible actions a player could take next in a text-based adventure game. Return them as a JSON array of short strings."
    prompt = f"Story context: {story_context}\nReturn 3-4 possible actions in a JSON array of strings."
    try:
        response = query_model(prompt, system_prompt)
        start = response.find('[')
        end = response.rfind(']') + 1
        if start != -1 and end != -1:
            return json.loads(response[start:end])
    except:
        pass
    return ["Look around", "Search the area", "Continue forward"]

def get_arc_hint(arc_progress: int) -> str:
    if arc_progress < 3:
        return "The world feels calm, but something bigger is stirring."
    elif arc_progress < 6:
        return "You sense unseen forces nudging you toward a hidden truth."
    else:
        return "The climax draws near, every choice feels heavy with consequence."

# Initialize session state
if "story" not in st.session_state:
    st.session_state.story = "You awaken in a quiet village at dawn..."
    st.session_state.choices = []
    st.session_state.arc_progress = 0
    st.session_state.suggested_actions = []
    st.session_state.last_choice = ""
    st.session_state.last_twist = ""
    st.session_state.is_loading = False
    st.session_state.world = WorldState()
    st.session_state.world.add_character("Old Man Jenkins", "An elderly villager with a long white beard and kind eyes.", ["wise", "friendly", "knowledgeable"])
    st.session_state.world.add_character("Captain Rourke", "The grizzled captain of the village guard, always on the lookout for trouble.", ["brave", "suspicious", "dutiful"])
    st.session_state.world.add_character("Mysterious Stranger", "A hooded figure who watches from the shadows.", ["mysterious", "elusive", "dangerous"])
    st.session_state.world.update_character_relationship("Old Man Jenkins", 2)
    st.session_state.world.update_character_relationship("Captain Rourke", -1)
    st.session_state.world.update_character_relationship("Mysterious Stranger", -3)

# Sidebar
with st.sidebar:
    st.header("📊 Story Stats")
    col1, col2 = st.columns(2)
    col1.metric("Choices Made", len(st.session_state.choices))
    col2.metric("Arc Progress", f"{min(100, st.session_state.arc_progress * 10)}%")
    st.markdown("---")
    st.header("👥 Characters")
    for char in st.session_state.world.characters.values():
        rel_icon = {
            RelationshipLevel.HOSTILE: "👿",
            RelationshipLevel.UNFRIENDLY: "😠",
            RelationshipLevel.NEUTRAL: "😐",
            RelationshipLevel.FRIENDLY: "🙂",
            RelationshipLevel.TRUSTED: "😊",
            RelationshipLevel.ALLY: "🤝"
        }.get(char.relationship, "❓")
        with st.expander(f"{rel_icon} {char.name} - {char.relationship.name}"):
            st.write(char.description)
            st.progress((char.relationship_points + 10) / 20, f"Relationship: {char.relationship.name} ({char.relationship_points})")
            if char.traits:
                cols = st.columns(3)
                for i, trait in enumerate(char.traits):
                    cols[i % 3].markdown(f"`{trait}`")
    st.markdown("---")
    st.header("🌍 World")
    st.markdown(f"**Location:** {st.session_state.world.current_location}")
    st.markdown(f"**Time of Day:** {st.session_state.world.time_of_day.title()}")
    with st.expander("🔧 Debug Info", expanded=False):
        st.json(st.session_state.world.to_dict())
        st.write("### Full Story")
        st.text_area("story_debug", value=st.session_state.story, height=200, label_visibility="collapsed")

# Main content
st.title("📖 Living Pages: A Dynamic Narrative System")
with st.container():
    st.markdown(f'<div class="story-container">{st.session_state.story}</div>', unsafe_allow_html=True)

if not st.session_state.suggested_actions:
    with st.spinner("Generating possible actions..."):
        st.session_state.suggested_actions = generate_suggested_actions(st.session_state.story)

st.subheader("What will you do next?")
cols = st.columns(2)
for i, action in enumerate(st.session_state.choices[-4:] + st.session_state.suggested_actions):
    if i < 4:
        with cols[i % 2]:
            if st.button(action, key=f"action_{i}", use_container_width=True):
                st.session_state.last_choice = action
                st.session_state.is_loading = True
                st.rerun()

with st.expander("Or type your own action"):
    custom_action = st.text_input("Your action:", key="custom_action")
    if st.button("Submit Custom Action"):
        if custom_action.strip():
            st.session_state.last_choice = custom_action
            st.session_state.is_loading = True
            st.rerun()

if st.session_state.is_loading and st.session_state.last_choice:
    with st.spinner("Continuing the story..."):
        user_choice = st.session_state.last_choice
        st.session_state.choices.append(user_choice)
        st.session_state.arc_progress += 1
        twist = ""
        if random.random() < 0.4:
            mentioned_chars = [char for char in st.session_state.world.characters.values() if char.name.lower() in st.session_state.story.lower()]
            if mentioned_chars:
                char = random.choice(mentioned_chars)
                interaction_type = random.choice(["help", "advice", "gift", "challenge", "threat", "observe", "question", "comment"])
                twist_prompt = f"Current story: {st.session_state.story}\nCharacter: {char.name}\nCharacter traits: {', '.join(char.traits)}\nRelationship: {char.relationship.name}\nGenerate a 1-2 sentence interaction."
                twist = query_model(twist_prompt, "You are a creative writer who creates engaging character interactions.")
                if interaction_type in ["help", "advice", "gift"]:
                    st.session_state.world.update_character_relationship(char.name, 1)
                elif interaction_type in ["threat", "challenge"]:
                    st.session_state.world.update_character_relationship(char.name, -1)
                char.last_interaction = "Just now"
        arc_hint = get_arc_hint(st.session_state.arc_progress)
        twist_section = f'NARRATIVE TWIST (if any):\n{twist}\n\n' if twist else ''
        prompt = f"""Continue the story:
CURRENT STORY:
{st.session_state.story}

PLAYER'S ACTION:
{user_choice}

{twist_section}NARRATIVE ARC HINT:
{arc_hint}

Continue the story in an engaging way, acknowledging the player's action and twists."""
        continuation = query_model(prompt, "You are a master storyteller. Continue the narrative engagingly.")
        update_text = f"\n\n> **{user_choice}**"
        if twist:
            update_text += f"\n\n*{twist}*\n"
        update_text += f"\n{continuation}"
        st.session_state.story += update_text
        st.session_state.suggested_actions = []
        st.session_state.is_loading = False
        st.session_state.last_choice = ""
        st.rerun()

st.markdown("<br><br>", unsafe_allow_html=True)

with st.expander("📝 Story Log", expanded=False):
    st.write("### Story So Far")
    st.text_area("", st.session_state.story, height=200)
    st.write("### Your Choices")
    for i, choice in enumerate(st.session_state.choices, 1):
        st.write(f"{i}. {choice}")
    if st.button("Start New Game"):
        st.session_state.clear()
        st.rerun()
